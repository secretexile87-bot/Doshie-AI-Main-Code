package org.diyoshi.assistant;

import android.Manifest;
import android.content.Context;
import android.content.Intent;
import android.net.Uri;
import android.os.Bundle;
import android.provider.Settings;
import android.speech.RecognitionListener;
import android.speech.RecognizerIntent;
import android.speech.SpeechRecognizer;
import android.util.Log;
import com.getcapacitor.JSObject;
import com.getcapacitor.PermissionState;
import com.getcapacitor.Plugin;
import com.getcapacitor.PluginCall;
import com.getcapacitor.PluginMethod;
import com.getcapacitor.annotation.CapacitorPlugin;
import com.getcapacitor.annotation.Permission;
import com.getcapacitor.annotation.PermissionCallback;
import java.util.ArrayList;
import java.util.Locale;

@CapacitorPlugin(
    name = "DiYoshiSpeech",
    permissions = {
        @Permission(alias = "microphone", strings = { Manifest.permission.RECORD_AUDIO })
    }
)
public class DiYoshiSpeechPlugin extends Plugin {
    private static final String TAG = "DiYoshiSpeech";
    private SpeechRecognizer speechRecognizer;
    private PluginCall activeCall;

    @PluginMethod
    public void startListening(PluginCall call) {
        try {
            if (getPermissionState("microphone") != PermissionState.GRANTED) {
                requestPermissionForAlias(
                    "microphone",
                    call,
                    "microphonePermissionCallback"
                );
                return;
            }
            beginListening(call);
        } catch (Throwable t) {
            Log.e(TAG, "Error in startListening", t);
            call.reject("Speech start error: " + t.getMessage());
        }
    }

    @PermissionCallback
    public void microphonePermissionCallback(PluginCall call) {
        try {
            if (getPermissionState("microphone") == PermissionState.GRANTED) {
                beginListening(call);
            } else {
                call.reject("Microphone permission was not granted.");
            }
        } catch (Throwable t) {
            Log.e(TAG, "Error in microphonePermissionCallback", t);
            call.reject("Permission error: " + t.getMessage());
        }
    }

    @PluginMethod
    public void openMicrophoneSettings(PluginCall call) {
        try {
            Intent intent = new Intent(
                Settings.ACTION_APPLICATION_DETAILS_SETTINGS,
                Uri.parse("package:" + getContext().getPackageName())
            );
            intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
            getContext().startActivity(intent);
            call.resolve();
        } catch (Throwable t) {
            Log.e(TAG, "Error opening settings", t);
            call.reject("Settings error: " + t.getMessage());
        }
    }

    @PluginMethod
    public void stopListening(PluginCall call) {
        try {
            if (getActivity() != null) {
                getActivity().runOnUiThread(() -> {
                    try {
                        if (speechRecognizer != null) {
                            speechRecognizer.stopListening();
                        }
                    } catch (Throwable ignored) {}
                    call.resolve();
                });
            } else {
                call.resolve();
            }
        } catch (Throwable t) {
            Log.e(TAG, "Error in stopListening", t);
            call.resolve();
        }
    }

    private void beginListening(PluginCall call) {
        if (getActivity() == null || getActivity().isFinishing()) {
            call.reject("Activity is not available.");
            return;
        }

        getActivity().runOnUiThread(() -> {
            try {
                if (activeCall != null) {
                    call.reject("Speech recognition is already active.");
                    return;
                }

                destroyRecognizer();

                Context ctx = getActivity();
                if (ctx == null) ctx = getContext();

                if (!SpeechRecognizer.isRecognitionAvailable(ctx)) {
                    call.reject("Android speech recognition is unavailable.");
                    return;
                }

                activeCall = call;
                speechRecognizer = SpeechRecognizer.createSpeechRecognizer(ctx);
                if (speechRecognizer == null) {
                    activeCall = null;
                    call.reject("Could not initialize SpeechRecognizer.");
                    return;
                }

                speechRecognizer.setRecognitionListener(new RecognitionListener() {
                    @Override
                    public void onReadyForSpeech(Bundle params) {}

                    @Override
                    public void onBeginningOfSpeech() {}

                    @Override
                    public void onRmsChanged(float rmsdB) {}

                    @Override
                    public void onBufferReceived(byte[] buffer) {}

                    @Override
                    public void onEndOfSpeech() {}

                    @Override
                    public void onError(int error) {
                        try {
                            finishError(errorMessage(error));
                        } catch (Throwable t) {
                            Log.e(TAG, "Error in onError handler", t);
                        }
                    }

                    @Override
                    public void onResults(Bundle results) {
                        try {
                            ArrayList<String> matches = results != null
                                ? results.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)
                                : null;

                            if (matches == null || matches.isEmpty()) {
                                finishError("No speech was recognized.");
                                return;
                            }

                            JSObject response = new JSObject();
                            response.put("text", matches.get(0));
                            float[] scores = results.getFloatArray(SpeechRecognizer.CONFIDENCE_SCORES);
                            if (scores != null && scores.length > 0) {
                                response.put("confidence", scores[0]);
                            }
                            finishSuccess(response);
                        } catch (Throwable t) {
                            Log.e(TAG, "Error in onResults handler", t);
                            finishError("Failed parsing speech results.");
                        }
                    }

                    @Override
                    public void onPartialResults(Bundle partialResults) {
                        try {
                            if (partialResults != null) {
                                ArrayList<String> matches = partialResults.getStringArrayList(
                                    SpeechRecognizer.RESULTS_RECOGNITION
                                );
                                if (matches != null && !matches.isEmpty()) {
                                    JSObject partial = new JSObject();
                                    partial.put("text", matches.get(0));
                                    notifyListeners("partialResult", partial);
                                }
                            }
                        } catch (Throwable ignored) {}
                    }

                    @Override
                    public void onEvent(int eventType, Bundle params) {}
                });

                Intent intent = new Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH);
                intent.putExtra(
                    RecognizerIntent.EXTRA_LANGUAGE_MODEL,
                    RecognizerIntent.LANGUAGE_MODEL_FREE_FORM
                );
                intent.putExtra(
                    RecognizerIntent.EXTRA_LANGUAGE,
                    call.getString("language", Locale.getDefault().toLanguageTag())
                );
                intent.putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, true);
                intent.putExtra(RecognizerIntent.EXTRA_MAX_RESULTS, 1);
                speechRecognizer.startListening(intent);
            } catch (Throwable t) {
                Log.e(TAG, "Fatal beginListening runner error", t);
                activeCall = null;
                destroyRecognizer();
                call.reject("Speech recognition could not start: " + t.getMessage());
            }
        });
    }

    private void finishSuccess(JSObject result) {
        PluginCall call = activeCall;
        activeCall = null;
        destroyRecognizer();
        if (call != null) {
            try {
                call.resolve(result);
            } catch (Throwable ignored) {}
        }
    }

    private void finishError(String message) {
        PluginCall call = activeCall;
        activeCall = null;
        destroyRecognizer();
        if (call != null) {
            try {
                call.reject(message);
            } catch (Throwable ignored) {}
        }
    }

    private void destroyRecognizer() {
        try {
            if (speechRecognizer != null) {
                speechRecognizer.destroy();
            }
        } catch (Throwable ignored) {
        } finally {
            speechRecognizer = null;
        }
    }

    private String errorMessage(int error) {
        switch (error) {
            case SpeechRecognizer.ERROR_AUDIO:
                return "Android could not read the microphone.";
            case SpeechRecognizer.ERROR_INSUFFICIENT_PERMISSIONS:
                return "Microphone permission is required.";
            case SpeechRecognizer.ERROR_NETWORK:
            case SpeechRecognizer.ERROR_NETWORK_TIMEOUT:
                return "Speech recognition needs a network connection.";
            case SpeechRecognizer.ERROR_NO_MATCH:
                return "I did not understand that. Please try again.";
            case SpeechRecognizer.ERROR_RECOGNIZER_BUSY:
                return "The speech recognizer is busy. Please try again.";
            case SpeechRecognizer.ERROR_SPEECH_TIMEOUT:
                return "I did not hear any speech.";
            case SpeechRecognizer.ERROR_SERVER:
                return "Android speech recognition is temporarily unavailable.";
            case SpeechRecognizer.ERROR_CLIENT:
                return "Speech recognition was stopped.";
            default:
                return "Speech recognition stopped with error " + error + ".";
        }
    }

    @Override
    protected void handleOnDestroy() {
        if (activeCall != null) {
            try {
                activeCall.reject("Speech recognition was closed.");
            } catch (Throwable ignored) {}
            activeCall = null;
        }
        if (getActivity() != null) {
            getActivity().runOnUiThread(this::destroyRecognizer);
        } else {
            destroyRecognizer();
        }
    }
}
