package ai.ezzio.office;

import android.annotation.SuppressLint;
import android.app.Activity;
import android.app.AlertDialog;
import android.content.SharedPreferences;
import android.graphics.Bitmap;
import android.os.Bundle;
import android.view.View;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceError;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ProgressBar;
import android.widget.TextView;
import android.widget.Toast;

/**
 * E-ZZIO AI Office — Sovereign Native Android Client Activity (v9.0.1).
 * Gère la connexion robuste au Master Governor E-ZzIO, le basculement d'IP (local, émulateur, LAN),
 * la gestion d'états d'erreur / hors-ligne, et le pont HITL.
 */
public class MainActivity extends Activity {

    private static final String PREFS_NAME = "EzzioPrefs";
    private static final String KEY_SERVER_URL = "server_url";
    private static final String DEFAULT_URL = "http://10.0.2.2:8001/"; // Default emulator host loopback

    private WebView mWebView;
    private ProgressBar mProgressBar;
    private LinearLayout mErrorOverlay;
    private TextView mTxtErrorMessage;
    private SharedPreferences mPrefs;
    private String mCurrentUrl;
    private boolean mHasError = false;

    @Override
    @SuppressLint("SetJavaScriptEnabled")
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        mPrefs = getSharedPreferences(PREFS_NAME, MODE_PRIVATE);
        mCurrentUrl = mPrefs.getString(KEY_SERVER_URL, DEFAULT_URL);

        mWebView = findViewById(R.id.webView);
        mProgressBar = findViewById(R.id.progressBar);
        mErrorOverlay = findViewById(R.id.errorOverlay);
        mTxtErrorMessage = findViewById(R.id.txtErrorMessage);

        Button btnRefresh = findViewById(R.id.btnRefresh);
        Button btnConfigServer = findViewById(R.id.btnConfigServer);
        Button btnRetry = findViewById(R.id.btnRetry);
        Button btnChangeUrl = findViewById(R.id.btnChangeUrl);

        btnRefresh.setOnClickListener(v -> reloadPage());
        btnRetry.setOnClickListener(v -> reloadPage());
        btnConfigServer.setOnClickListener(v -> showServerConfigDialog());
        btnChangeUrl.setOnClickListener(v -> showServerConfigDialog());

        setupWebView();
        loadUrl(mCurrentUrl);
    }

    @SuppressLint("SetJavaScriptEnabled")
    private void setupWebView() {
        WebSettings settings = mWebView.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        settings.setDatabaseEnabled(true);
        settings.setCacheMode(WebSettings.LOAD_DEFAULT);
        settings.setAllowFileAccess(false);
        settings.setAllowContentAccess(false);
        settings.setBuiltInZoomControls(true);
        settings.setDisplayZoomControls(false);
        settings.setUserAgentString(settings.getUserAgentString() + " EzzioAndroidNative/9.0.1");

        mWebView.setWebViewClient(new WebViewClient() {
            @Override
            public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                view.loadUrl(request.getUrl().toString());
                return true;
            }

            @Override
            public void onPageStarted(WebView view, String url, Bitmap favicon) {
                super.onPageStarted(view, url, favicon);
                mHasError = false;
                mProgressBar.setVisibility(View.VISIBLE);
                mErrorOverlay.setVisibility(View.GONE);
            }

            @Override
            public void onPageFinished(WebView view, String url) {
                super.onPageFinished(view, url);
                mProgressBar.setVisibility(View.GONE);
                if (!mHasError) {
                    mErrorOverlay.setVisibility(View.GONE);
                    mWebView.setVisibility(View.VISIBLE);
                }
            }

            @Override
            public void onReceivedError(WebView view, WebResourceRequest request, WebResourceError error) {
                super.onReceivedError(view, request, error);
                if (request.isForMainFrame()) {
                    mHasError = true;
                    mProgressBar.setVisibility(View.GONE);
                    mWebView.setVisibility(View.GONE);
                    mErrorOverlay.setVisibility(View.VISIBLE);
                    mTxtErrorMessage.setText("Impossible de contacter E-ZzIO :\n" + mCurrentUrl + "\nCode: " + error.getErrorCode());
                }
            }
        });

        mWebView.setWebChromeClient(new WebChromeClient() {
            @Override
            public void onProgressChanged(WebView view, int newProgress) {
                if (newProgress >= 100) {
                    mProgressBar.setVisibility(View.GONE);
                } else if (!mHasError) {
                    mProgressBar.setVisibility(View.VISIBLE);
                }
            }
        });
    }

    private void loadUrl(String url) {
        mCurrentUrl = url;
        mWebView.loadUrl(url);
    }

    private void reloadPage() {
        mHasError = false;
        mErrorOverlay.setVisibility(View.GONE);
        mWebView.setVisibility(View.VISIBLE);
        mWebView.reload();
    }

    private void showServerConfigDialog() {
        AlertDialog.Builder builder = new AlertDialog.Builder(this);
        builder.setTitle("Configuration Master Governor");

        final EditText input = new EditText(this);
        input.setHint("http://192.168.1.x:8001/ ou http://10.0.2.2:8001/");
        input.setText(mCurrentUrl);
        builder.setView(input);

        builder.setPositiveButton("Enregistrer & Connecter", (dialog, which) -> {
            String newUrl = input.getText().toString().trim();
            if (!newUrl.isEmpty()) {
                if (!newUrl.endsWith("/")) {
                    newUrl += "/";
                }
                mCurrentUrl = newUrl;
                mPrefs.edit().putString(KEY_SERVER_URL, mCurrentUrl).apply();
                loadUrl(mCurrentUrl);
                Toast.makeText(MainActivity.this, "Connexion vers : " + mCurrentUrl, Toast.LENGTH_SHORT).show();
            }
        });

        builder.setNegativeButton("Annuler", (dialog, which) -> dialog.cancel());
        builder.show();
    }

    @Override
    public void onBackPressed() {
        if (mWebView != null && mWebView.canGoBack()) {
            mWebView.goBack();
        } else {
            super.onBackPressed();
        }
    }
}
