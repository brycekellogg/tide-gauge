package org.warmbeachtides.tidegauge.ui;

import android.os.Bundle;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;

import androidx.annotation.NonNull;
import androidx.annotation.Nullable;
import androidx.fragment.app.Fragment;
import androidx.viewpager2.widget.ViewPager2;

import org.warmbeachtides.tidegauge.R;

public class TideChartPageFragment extends Fragment {

    TideChartAdapter tideChartAdapter;
    ViewPager2 viewPager;

    public View onCreateView(@NonNull LayoutInflater inflater, ViewGroup container, Bundle savedInstanceState) {
        View root = inflater.inflate(R.layout.fragment_page_tidechart, container, false);
        return root;
    }

    @Override
    public void onViewCreated(@NonNull View view, @Nullable Bundle savedInstanceState) {
        tideChartAdapter = new TideChartAdapter(this);
        viewPager = view.findViewById(R.id.tidechart_pager);
        viewPager.setAdapter(tideChartAdapter);
        viewPager.setCurrentItem(tideChartAdapter.getItemCount()-1, false);
    }
}