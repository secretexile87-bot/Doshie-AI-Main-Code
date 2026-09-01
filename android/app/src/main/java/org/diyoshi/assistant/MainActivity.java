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

public class MainActivity extends BridgeActivity {
    private static final String UPDATE_ENDPOINT =
        "https://hermes-duran-tecra-a60-m.tail50b4c5.ts.net:8443/app-version?client=android";

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        registerPlugin(DiYoshiSpeechPlugin.class);
        super.onCreate(savedInstanceState);
        installSafeAreaBridge();
        openVerifiedDiYoshiLink(getIntent());
        checkForUpdate();
        // Updates are checked against the trusted Doshie APK channel.
    }

    private void installSafeAreaBridge() {
        ViewCompat.setOnApplyWindowInsetsListener(bridge.getWebView(), (view, insets) -> {
            Insets bars = insets.getInsets(
                WindowInsetsCompat.Type.systemBars()
                    | WindowInsetsCompat.Type.displayCutout()
            );
            float density = getResources().getDisplayMetrics().density;
            int top = Math.round(bars.top / density);
            int bottom = Math.round(bars.bottom / density);
            String script = "document.documentElement.style.setProperty('--native-safe-top','"
                + top + "px');document.documentElement.style.setProperty('--native-safe-bottom','"
                + bottom + "px');";
            view.post(() -> bridge.getWebView().evaluateJavascript(script, null));
            return insets;
        });
        ViewCompat.requestApplyInsets(bridge.getWebView());
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
                if (release == null) return;
                String latest = release.optString("version", "");
                String downloadUrl = release.optString("url", "");
                String current = getPackageManager()
                    .getPackageInfo(getPackageName(), 0).versionName;
                if (!downloadUrl.isEmpty() && compareVersions(latest, current) > 0) {
                    runOnUiThread(() -> showUpdateDialog(latest, downloadUrl));
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
                : "https://hermes-duran-tecra-a60-m.tail50b4c5.ts.net:8443"
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
        if (!"hermes-duran-tecra-a60-m.tail50b4c5.ts.net".equalsIgnoreCase(uri.getHost())) return;
        if (uri.getPath() == null || !uri.getPath().startsWith("/login")) return;
        bridge.getWebView().post(() -> bridge.getWebView().loadUrl(uri.toString()));
    }
}
