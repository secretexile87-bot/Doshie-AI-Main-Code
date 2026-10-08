package org.diyoshi.assistant;

import android.app.AlertDialog;
import android.content.ActivityNotFoundException;
import android.content.Intent;
import android.net.Uri;
import android.os.Bundle;
import android.widget.Toast;
import androidx.core.graphics.Insets;
import androidx.core.view.ViewCompat;
import androidx.core.view.WindowInsetsCompat;
import com.getcapacitor.BridgeActivity;
import org.json.JSONObject;
import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

import android.view.View;
import android.view.ViewGroup;
import androidx.activity.OnBackPressedCallback;

public class MainActivity extends BridgeActivity {
    private static final String UPDATE_ENDPOINT =
        "https://acer-nitro.tail50b4c5.ts.net/app-version?client=android";

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        registerPlugin(DiYoshiSpeechPlugin.class);
        super.onCreate(savedInstanceState);

        // Ensure microphone permissions are prompted and granted for speech recognition and live voice
        if (checkSelfPermission(android.Manifest.permission.RECORD_AUDIO) != android.content.pm.PackageManager.PERMISSION_GRANTED) {
            requestPermissions(new String[]{
                android.Manifest.permission.RECORD_AUDIO,
                android.Manifest.permission.MODIFY_AUDIO_SETTINGS
            }, 101);
        }

        installSafeAreaBridge();
        installBackButtonHandler();
        openVerifiedDiYoshiLink(getIntent());
        checkForUpdate();
        // Updates are checked against the trusted Doshie APK channel.
    }

    private void installBackButtonHandler() {
        getOnBackPressedDispatcher().addCallback(this, new OnBackPressedCallback(true) {
            @Override
            public void handleOnBackPressed() {
                if (bridge == null || bridge.getWebView() == null) {
                    setEnabled(false);
                    getOnBackPressedDispatcher().onBackPressed();
                    setEnabled(true);
                    return;
                }

                bridge.getWebView().evaluateJavascript(
                    "(function() { " +
                    "  if (typeof window.__doshieHandleBack === 'function' && window.__doshieHandleBack()) { " +
                    "    return 'handled'; " +
                    "  } " +
                    "  return 'unhandled'; " +
                    "})()",
                    result -> {
                        String clean = result != null ? result.replace("\"", "").trim() : "";
                        if ("handled".equals(clean)) {
                            // Handled by Doshie React UI (closed a modal or drawer)
                            return;
                        }

                        runOnUiThread(() -> {
                            String currentUrl = bridge.getWebView().getUrl();
                            // If user is inside an external tool view, bring them back to Doshie
                            if (currentUrl != null && (currentUrl.contains("/voice-studio") || currentUrl.contains("/control") || currentUrl.contains("/live"))) {
                                bridge.getWebView().loadUrl("https://acer-nitro.tail50b4c5.ts.net/mansion?app=android-0.9.6");
                                return;
                            }

                            if (bridge.getWebView().canGoBack()) {
                                bridge.getWebView().goBack();
                                return;
                            }

                            // If on main screen with nothing open, minimize smoothly to home
                            moveTaskToBack(true);
                        });
                    }
                );
            }
        });
    }

    private void installSafeAreaBridge() {
        View webView = bridge.getWebView();
        ViewGroup.LayoutParams initialLp = webView.getLayoutParams();
        final int initialBottomMargin = (initialLp instanceof ViewGroup.MarginLayoutParams)
                ? ((ViewGroup.MarginLayoutParams) initialLp).bottomMargin
                : 0;

        ViewCompat.setOnApplyWindowInsetsListener(webView, (view, insets) -> {
            Insets bars = insets.getInsets(
                WindowInsetsCompat.Type.systemBars()
                    | WindowInsetsCompat.Type.displayCutout()
            );
            Insets ime = insets.getInsets(WindowInsetsCompat.Type.ime());

            // Adjust WebView bottom margin so it physically shrinks above the soft keyboard
            ViewGroup.LayoutParams lp = view.getLayoutParams();
            if (lp instanceof ViewGroup.MarginLayoutParams) {
                ViewGroup.MarginLayoutParams mlp = (ViewGroup.MarginLayoutParams) lp;
                int targetBottomMargin = initialBottomMargin + ime.bottom;
                if (mlp.bottomMargin != targetBottomMargin) {
                    mlp.bottomMargin = targetBottomMargin;
                    view.setLayoutParams(mlp);
                }
            }

            float density = getResources().getDisplayMetrics().density;
            int top = Math.round(bars.top / density);
            int bottom = Math.round(bars.bottom / density);
            int imeHeight = Math.round(ime.bottom / density);
            boolean isKeyboardOpen = ime.bottom > 0;

            String script = "document.documentElement.style.setProperty('--native-safe-top','"
                + top + "px');"
                + "document.documentElement.style.setProperty('--native-safe-bottom','"
                + bottom + "px');"
                + "document.documentElement.style.setProperty('--native-keyboard-height','"
                + imeHeight + "px');"
                + "window.dispatchEvent(new CustomEvent('nativeKeyboardChange', { detail: { height: "
                + imeHeight + ", isOpen: " + (isKeyboardOpen ? "true" : "false") + " } }));";
            view.post(() -> bridge.getWebView().evaluateJavascript(script, null));
            return insets;
        });
        ViewCompat.requestApplyInsets(webView);
    }

    private void checkForUpdate() {
        ExecutorService executor = Executors.newSingleThreadExecutor();
        executor.execute(() -> {
            HttpURLConnection connection = null;
            try {
                URL endpoint = new URL(UPDATE_ENDPOINT);
                connection = (HttpURLConnection) endpoint.openConnection();
                connection.setConnectTimeout(4500);
                connection.setReadTimeout(6500);
                connection.setRequestMethod("GET");
                if (connection.getResponseCode() != HttpURLConnection.HTTP_OK) return;

                StringBuilder body = new StringBuilder();
                try (BufferedReader reader = new BufferedReader(
                        new InputStreamReader(connection.getInputStream()))) {
                    String line;
                    while ((line = reader.readLine()) != null) body.append(line);
                }

                JSONObject root = new JSONObject(body.toString());
                JSONObject release = root.optJSONObject("android");
                if (release == null && root.optJSONObject("releases") != null) {
                    release = root.optJSONObject("releases").optJSONObject("android");
                }
                if (release == null) return;
                String latest = release.optString("version", root.optString("version", ""));
                String downloadUrl = release.optString("url", "");
                if (downloadUrl.isEmpty() && release.has("file")) {
                    downloadUrl = "/static/downloads/" + release.optString("file");
                }
                String current = getPackageManager()
                    .getPackageInfo(getPackageName(), 0).versionName;
                final String finalDownloadUrl = downloadUrl;
                if (!finalDownloadUrl.isEmpty() && compareVersions(latest, current) > 0) {
                    runOnUiThread(() -> showUpdateDialog(latest, finalDownloadUrl));
                }
            } catch (Exception ignored) {
                // Offline devices keep using the installed app.
            } finally {
                if (connection != null) connection.disconnect();
                executor.shutdown();
            }
        });
    }

    private void showUpdateDialog(String latest, String downloadUrl) {
        if (isFinishing()) return;
        new AlertDialog.Builder(this)
            .setTitle("DiYoshi update available")
            .setMessage(
                "Version " + latest + " is ready. Download it from your private "
                    + "Tailscale server; Android will ask you to confirm installation."
            )
            .setNegativeButton("Later", null)
            .setPositiveButton("Download", (dialog, which) -> openUpdate(downloadUrl))
            .show();
    }

    private void openUpdate(String downloadUrl) {
        try {
            String resolvedUrl = downloadUrl.startsWith("http")
                ? downloadUrl
                : "https://acer-nitro.tail50b4c5.ts.net"
                    + (downloadUrl.startsWith("/") ? "" : "/")
                    + downloadUrl;
            startActivity(new Intent(Intent.ACTION_VIEW, Uri.parse(resolvedUrl)));
        } catch (ActivityNotFoundException error) {
            Toast.makeText(
                this,
                "No browser is available to download the update.",
                Toast.LENGTH_LONG
            ).show();
        }
    }

    private static int compareVersions(String left, String right) {
        String[] a = String.valueOf(left).split("[^0-9]+");
        String[] b = String.valueOf(right).split("[^0-9]+");
        int count = Math.max(a.length, b.length);
        for (int index = 0; index < count; index++) {
            int leftPart = part(a, index);
            int rightPart = part(b, index);
            if (leftPart != rightPart) return Integer.compare(leftPart, rightPart);
        }
        return 0;
    }

    private static int part(String[] parts, int index) {
        if (index >= parts.length || parts[index].isEmpty()) return 0;
        try {
            return Integer.parseInt(parts[index]);
        } catch (NumberFormatException error) {
            return 0;
        }
    }

    @Override
    protected void onNewIntent(Intent intent) {
        super.onNewIntent(intent);
        setIntent(intent);
        openVerifiedDiYoshiLink(intent);
    }

    private void openVerifiedDiYoshiLink(Intent intent) {
        Uri uri = intent == null ? null : intent.getData();
        if (uri == null || !"https".equalsIgnoreCase(uri.getScheme())) return;
        String host = uri.getHost();
        if (host == null) return;
        if (!"acer-nitro.tail50b4c5.ts.net".equalsIgnoreCase(host) && !"hermes-doshie.tail50b4c5.ts.net".equalsIgnoreCase(host)) return;
        if (uri.getPath() == null || !uri.getPath().startsWith("/login")) return;
        bridge.getWebView().post(() -> bridge.getWebView().loadUrl(uri.toString()));
    }

    @Override
    public void onConfigurationChanged(android.content.res.Configuration newConfig) {
        super.onConfigurationChanged(newConfig);
        android.webkit.WebView webView = bridge.getWebView();
        if (webView != null) {
            ViewCompat.requestApplyInsets(webView);
            webView.post(() -> webView.evaluateJavascript(
                "window.dispatchEvent(new Event('resize'));", null
            ));
        }
    }
}
