package org.diyoshi.assistant;

import android.os.Handler;
import android.os.Looper;
import android.util.Log;
import androidx.annotation.NonNull;
import androidx.biometric.BiometricManager;
import androidx.biometric.BiometricPrompt;
import androidx.core.content.ContextCompat;
import androidx.fragment.app.FragmentActivity;
import com.getcapacitor.JSObject;
import com.getcapacitor.Plugin;
import com.getcapacitor.PluginCall;
import com.getcapacitor.PluginMethod;
import com.getcapacitor.annotation.CapacitorPlugin;
import java.util.concurrent.Executor;

@CapacitorPlugin(name = "DiYoshiBiometric")
public class DiYoshiBiometricPlugin extends Plugin {
    private static final String TAG = "DiYoshiBiometric";

    @PluginMethod
    public void isAvailable(PluginCall call) {
        try {
            BiometricManager biometricManager = BiometricManager.from(getContext());
            int canAuth = biometricManager.canAuthenticate(
                BiometricManager.Authenticators.BIOMETRIC_STRONG
                | BiometricManager.Authenticators.BIOMETRIC_WEAK
                | BiometricManager.Authenticators.DEVICE_CREDENTIAL
            );

            JSObject ret = new JSObject();
            if (canAuth == BiometricManager.BIOMETRIC_SUCCESS) {
                ret.put("isAvailable", true);
                ret.put("hasHardware", true);
                ret.put("isEnrolled", true);
                ret.put("biometryType", "fingerprint");
            } else if (canAuth == BiometricManager.BIOMETRIC_ERROR_NONE_ENROLLED) {
                ret.put("isAvailable", false);
                ret.put("hasHardware", true);
                ret.put("isEnrolled", false);
                ret.put("reason", "No fingerprints or credentials enrolled on this Android device");
            } else {
                ret.put("isAvailable", false);
                ret.put("hasHardware", false);
                ret.put("isEnrolled", false);
                ret.put("reason", "Biometrics not available on this device (" + canAuth + ")");
            }
            call.resolve(ret);
        } catch (Throwable t) {
            Log.e(TAG, "Error checking biometric availability", t);
            JSObject ret = new JSObject();
            ret.put("isAvailable", false);
            ret.put("error", t.getMessage());
            call.resolve(ret);
        }
    }

    @PluginMethod
    public void authenticate(PluginCall call) {
        String title = call.getString("title", "Doshie Biometric Verification");
        String subtitle = call.getString("subtitle", "Scan fingerprint or face to verify");
        String description = call.getString("description", "Secure access to your Doshie profile");

        if (!(getActivity() instanceof FragmentActivity)) {
            call.reject("Current activity does not support BiometricPrompt");
            return;
        }

        FragmentActivity activity = (FragmentActivity) getActivity();
        new Handler(Looper.getMainLooper()).post(() -> {
            try {
                Executor executor = ContextCompat.getMainExecutor(activity);
                BiometricPrompt.PromptInfo promptInfo = new BiometricPrompt.PromptInfo.Builder()
                    .setTitle(title)
                    .setSubtitle(subtitle)
                    .setDescription(description)
                    .setAllowedAuthenticators(
                        BiometricManager.Authenticators.BIOMETRIC_STRONG
                        | BiometricManager.Authenticators.BIOMETRIC_WEAK
                        | BiometricManager.Authenticators.DEVICE_CREDENTIAL
                    )
                    .build();

                BiometricPrompt biometricPrompt = new BiometricPrompt(
                    activity,
                    executor,
                    new BiometricPrompt.AuthenticationCallback() {
                        @Override
                        public void onAuthenticationError(int errorCode, @NonNull CharSequence errString) {
                            super.onAuthenticationError(errorCode, errString);
                            if (errorCode == BiometricPrompt.ERROR_USER_CANCELED
                                || errorCode == BiometricPrompt.ERROR_NEGATIVE_BUTTON) {
                                call.reject("Authentication cancelled", "USER_CANCELED");
                            } else {
                                call.reject(errString.toString(), String.valueOf(errorCode));
                            }
                        }

                        @Override
                        public void onAuthenticationSucceeded(@NonNull BiometricPrompt.AuthenticationResult result) {
                            super.onAuthenticationSucceeded(result);
                            JSObject ret = new JSObject();
                            ret.put("success", true);
                            ret.put("verified", true);
                            call.resolve(ret);
                        }

                        @Override
                        public void onAuthenticationFailed() {
                            super.onAuthenticationFailed();
                            // Android BiometricPrompt UI displays "Not recognized. Try again." automatically.
                        }
                    }
                );

                biometricPrompt.authenticate(promptInfo);
            } catch (Throwable t) {
                Log.e(TAG, "Biometric authentication failed to launch", t);
                call.reject("Failed to display biometric prompt: " + t.getMessage());
            }
        });
    }
}
