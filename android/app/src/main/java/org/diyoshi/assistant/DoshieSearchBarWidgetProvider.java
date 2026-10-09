package org.diyoshi.assistant;

import android.app.PendingIntent;
import android.appwidget.AppWidgetManager;
import android.appwidget.AppWidgetProvider;
import android.content.Context;
import android.content.Intent;
import android.net.Uri;
import android.widget.RemoteViews;

public class DoshieSearchBarWidgetProvider extends AppWidgetProvider {

    @Override
    public void onUpdate(Context context, AppWidgetManager appWidgetManager, int[] appWidgetIds) {
        for (int appWidgetId : appWidgetIds) {
            updateAppWidget(context, appWidgetManager, appWidgetId);
        }
    }

    static void updateAppWidget(Context context, AppWidgetManager appWidgetManager, int appWidgetId) {
        RemoteViews views = new RemoteViews(context.getPackageName(), R.layout.widget_doshie_search_bar);

        // Chat / Search intent
        Intent chatIntent = new Intent(context, MainActivity.class);
        chatIntent.setAction("org.diyoshi.assistant.ACTION_CHAT");
        chatIntent.putExtra("doshie_action", "chat");
        chatIntent.setData(Uri.parse("doshie://action/chat"));
        chatIntent.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TOP | Intent.FLAG_ACTIVITY_SINGLE_TOP);
        PendingIntent chatPendingIntent = PendingIntent.getActivity(
            context, 101, chatIntent,
            PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE
        );
        views.setOnClickPendingIntent(R.id.widget_search_bar_root, chatPendingIntent);
        views.setOnClickPendingIntent(R.id.widget_search_text, chatPendingIntent);
        views.setOnClickPendingIntent(R.id.widget_doshie_logo, chatPendingIntent);

        // Music player intent
        Intent musicIntent = new Intent(context, MainActivity.class);
        musicIntent.setAction("org.diyoshi.assistant.ACTION_MUSIC");
        musicIntent.putExtra("doshie_action", "music");
        musicIntent.setData(Uri.parse("doshie://action/music"));
        musicIntent.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TOP | Intent.FLAG_ACTIVITY_SINGLE_TOP);
        PendingIntent musicPendingIntent = PendingIntent.getActivity(
            context, 102, musicIntent,
            PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE
        );
        views.setOnClickPendingIntent(R.id.widget_btn_music, musicPendingIntent);

        // Live Voice Mic intent
        Intent voiceIntent = new Intent(context, MainActivity.class);
        voiceIntent.setAction("org.diyoshi.assistant.ACTION_LIVE_VOICE");
        voiceIntent.putExtra("doshie_action", "live_voice");
        voiceIntent.setData(Uri.parse("doshie://action/live_voice"));
        voiceIntent.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TOP | Intent.FLAG_ACTIVITY_SINGLE_TOP);
        PendingIntent voicePendingIntent = PendingIntent.getActivity(
            context, 103, voiceIntent,
            PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE
        );
        views.setOnClickPendingIntent(R.id.widget_btn_mic, voicePendingIntent);

        appWidgetManager.updateAppWidget(appWidgetId, views);
    }
}
