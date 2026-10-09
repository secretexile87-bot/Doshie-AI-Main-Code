package org.diyoshi.assistant;

import android.app.PendingIntent;
import android.appwidget.AppWidgetManager;
import android.appwidget.AppWidgetProvider;
import android.content.Context;
import android.content.Intent;
import android.net.Uri;
import android.widget.RemoteViews;

public class DoshieQuickWakeWidgetProvider extends AppWidgetProvider {

    @Override
    public void onUpdate(Context context, AppWidgetManager appWidgetManager, int[] appWidgetIds) {
        for (int appWidgetId : appWidgetIds) {
            updateAppWidget(context, appWidgetManager, appWidgetId);
        }
    }

    static void updateAppWidget(Context context, AppWidgetManager appWidgetManager, int appWidgetId) {
        RemoteViews views = new RemoteViews(context.getPackageName(), R.layout.widget_doshie_quick_wake);

        // 1-tap Live Voice Quick Wake intent
        Intent voiceIntent = new Intent(context, MainActivity.class);
        voiceIntent.setAction("org.diyoshi.assistant.ACTION_LIVE_VOICE");
        voiceIntent.putExtra("doshie_action", "live_voice");
        voiceIntent.setData(Uri.parse("doshie://action/live_voice"));
        voiceIntent.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TOP | Intent.FLAG_ACTIVITY_SINGLE_TOP);
        PendingIntent voicePendingIntent = PendingIntent.getActivity(
            context, 201, voiceIntent,
            PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE
        );
        views.setOnClickPendingIntent(R.id.widget_btn_quick_wake, voicePendingIntent);

        appWidgetManager.updateAppWidget(appWidgetId, views);
    }
}
