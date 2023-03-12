package org.warmbeachtides.tidegauge.ui;

import android.os.Bundle;
import android.util.Log;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.TextView;

import androidx.annotation.NonNull;
import androidx.annotation.Nullable;
import androidx.fragment.app.Fragment;

import com.github.mikephil.charting.charts.LineChart;
import com.github.mikephil.charting.components.AxisBase;
import com.github.mikephil.charting.components.Description;
import com.github.mikephil.charting.components.XAxis;
import com.github.mikephil.charting.components.YAxis;
import com.github.mikephil.charting.data.Entry;
import com.github.mikephil.charting.data.LineData;
import com.github.mikephil.charting.data.LineDataSet;
import com.github.mikephil.charting.formatter.IAxisValueFormatter;
import com.github.mikephil.charting.formatter.ValueFormatter;
import com.github.mikephil.charting.renderer.XAxisRenderer;
import com.github.mikephil.charting.utils.Transformer;
import com.github.mikephil.charting.utils.ViewPortHandler;
import com.loopj.android.http.*;
import cz.msebera.android.httpclient.Header;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;
import org.warmbeachtides.tidegauge.R;

import java.nio.charset.StandardCharsets;
import java.text.DateFormat;
import java.text.ParseException;
import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Calendar;
import java.util.Date;
import java.util.Locale;
import java.util.TimeZone;
import java.util.concurrent.TimeUnit;


// Instances of this class are fragments representing a single
// object in our collection.
public class TideChartFragment extends Fragment {

    private LineChart chart;

    @Nullable
    @Override
    public View onCreateView(@NonNull LayoutInflater inflater, @Nullable ViewGroup container, @Nullable Bundle savedInstanceState) {
        return inflater.inflate(R.layout.fragment_tidechart, container, false);
    }

    @Override
    public void onViewCreated(@NonNull View view, @Nullable Bundle savedInstanceState) {
        Bundle args = getArguments();
        Date targetDate = (Date) args.getSerializable("DATE");
        SimpleDateFormat displayFormatter = new SimpleDateFormat("MMM d, yyyy", Locale.ENGLISH);
        ((TextView) view.findViewById(R.id.textViewDate)).setText(displayFormatter.format(targetDate));

        // Get start and end of the desired day
        Calendar cal = Calendar.getInstance();
        cal.setTime(targetDate);
        cal.set(Calendar.HOUR_OF_DAY, 0);
        cal.set(Calendar.MINUTE, 0);
        cal.set(Calendar.SECOND, 0);
        Date startDate = cal.getTime();
        cal.add(Calendar.DAY_OF_MONTH, 1);
        Date endDate = cal.getTime();

        // Get strings for GTM
        SimpleDateFormat formatter = new SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss", Locale.ENGLISH);
        TimeZone gmtTime = TimeZone.getTimeZone("GMT");
        formatter.setTimeZone(gmtTime);
        String startTimestamp = formatter.format(startDate);
        String endTimestamp = formatter.format(endDate);

        // Build query URL
        String url = "https://api.warmbeachtides.org/sensor-data?" +
                     "timestamp_gt=" + startTimestamp + "&" +
                     "timestamp_lt=" + endTimestamp;

        // Make query to cloud
        AsyncHttpClient client = new AsyncHttpClient();
        client.addHeader("x-api-key", "dpifJuDLFr6UcdGv7Iq742T5ZJ3fHbuKa6I0zYBq");
        client.get(url, new AsyncHttpResponseHandler() {

            @Override
            public void onSuccess(int statusCode, Header[] headers, byte[] response) {
                try {
                    // Data should be returned as a JSON array
                    JSONArray data = new JSONArray(new String(response));

                    // Fill plot with data
                    chart = getView().findViewById(R.id.tidechart);
                    ArrayList<Entry> values = new ArrayList<>();
                    for (int i = 0; i < data.length(); i++) {

                        // Get data from JSON
                        JSONObject obj = data.getJSONObject(i);
                        int value = obj.getInt("distance");
                        String timestampStr = obj.getString("timestamp");

                        // Convert timestamp to unix time
                        Date timestamp = formatter.parse(timestampStr);
                        long unixTime = timestamp.getTime() / 1000;

                        Log.i("Date = ", timestamp.toString());
                        Log.i("Unix = ", Long.toString(unixTime));

                        // Convert distance to height
                        values.add(new Entry(unixTime, obj.getInt("distance")));
                    }
                    // Format the data set
                    LineDataSet lineDataSet = new LineDataSet(values, "");
                    lineDataSet.setDrawCircles(false);
                    lineDataSet.setMode(LineDataSet.Mode.LINEAR);

                    // Format the line
                    LineData lineData = new LineData(lineDataSet);
                    chart.getLegend().setEnabled(false);
                    chart.getDescription().setEnabled(false);



                    // Format Y axis
                    chart.getAxisRight().setDrawLabels(false);
                    YAxis leftAxis = chart.getAxisLeft();
                    leftAxis.setPosition(YAxis.YAxisLabelPosition.OUTSIDE_CHART);
                    leftAxis.setAxisMinimum(-30f);
                    leftAxis.setAxisMaximum(15f);

                    // Format X axis
                    XAxis xAxis = chart.getXAxis();


                    chart.setXAxisRenderer(new SpecificPositionLabelsXAxisRenderer(chart.getViewPortHandler(), xAxis, chart.getTransformer(leftAxis.getAxisDependency())));

                    xAxis.setValueFormatter(new ValueFormatter() {
                        private final SimpleDateFormat mFormat = new SimpleDateFormat("hh:mm", Locale.ENGLISH);
                        public String getAxisLabel(float value, AxisBase axis) {
                            Date date = new Date((long) value*1000);
                            Log.i("Value = ", Long.toString((long) value));
                            //Log.i("Date = ", date.toString());
                            return mFormat.format(date);
                        }
                    });






                    xAxis.setPosition(XAxis.XAxisPosition.BOTTOM);
                    xAxis.setTextSize(10f);
                    xAxis.setDrawAxisLine(true);
                    xAxis.setDrawGridLines(false);
                    //xAxis.setCenterAxisLabels(true);

                    Log.i("min = ", Float.toString(lineData.getXMin()));
                    Log.i("max = ", Float.toString(lineData.getXMax()));

                    xAxis.setAxisMinimum(startDate.getTime() / 1000);
                    xAxis.setAxisMaximum(endDate.getTime() / 1000);
                    //xAxis.setGranularity(100);
                    //xAxis.setGranularityEnabled(true);
                    //xAxis.setLabelCount(5, true);




                    // Assign the data to the chart and
                    // trigger a refresh to draw it
                    chart.setData(lineData);
                    chart.invalidate();


                    Log.i("data", data.toString());
                } catch (JSONException | ParseException e) {
                    e.printStackTrace();
                }
            }

            @Override
            public void onFailure(int statusCode, Header[] headers, byte[] errorResponse, Throwable e) {
                Log.i("BRYCE HTTP onFailure()", Integer.toString(statusCode));
            }
        });
    }

    private class SpecificPositionLabelsXAxisRenderer extends XAxisRenderer {

        public SpecificPositionLabelsXAxisRenderer(ViewPortHandler viewPortHandler, XAxis xAxis, Transformer trans) {
            super(viewPortHandler, xAxis, trans);
        }

        @Override
        protected void computeAxisValues(float min, float max) {
            Log.i("Date = ", "BRYCE BRYCE BRYCE");

            mAxis.mEntryCount = 13;
            mAxis.mEntries = new float[]{
                    1617692400, // 00:00
                    1617699600, // 02:00
                    1617706800, // 04:00
                    1617714000, // 06:00
                    1617721200, // 08:00
                    1617728400, // 10:00
                    1617735600, // 12:00
                    1617742800, // 02:00
                    1617750000, // 04:00
                    1617757200, // 06:00
                    1617764400, // 08:00
                    1617771600, // 10:00
                    1617775500// 12:00


            };
            computeSize();

            super.computeAxisValues(min, max);
        }
    }
}