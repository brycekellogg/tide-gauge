package org.warmbeachtides.tidegauge.ui;

import android.os.Bundle;

import androidx.fragment.app.Fragment;
import androidx.viewpager2.adapter.FragmentStateAdapter;
import org.jetbrains.annotations.NotNull;

import java.util.Calendar;
import java.util.Date;

public class TideChartAdapter extends FragmentStateAdapter {
    public TideChartAdapter(Fragment fragment) {
        super(fragment);
    }

    @NotNull
    @Override
    public Fragment createFragment(int position) {

        // Calculate date based on position. Today is
        // the rightmost position (getItemCount() - 1).
        Calendar cal = Calendar.getInstance();
        cal.setTime(new Date());
        cal.add(Calendar.DATE, 1 - (getItemCount() - position));
        Date date = cal.getTime();


        // Return a new fragment instance
        Fragment fragment = new TideChartFragment();
        Bundle args = new Bundle();

        // Send the selected date to the fragment
        args.putSerializable("DATE", date);
        fragment.setArguments(args);

        return fragment;
    }

    @Override
    public int getItemCount() {
        return 100;
    }
}
