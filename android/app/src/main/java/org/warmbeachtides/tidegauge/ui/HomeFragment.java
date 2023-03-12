package org.warmbeachtides.tidegauge.ui;

import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.util.Log;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;

import androidx.annotation.NonNull;
import androidx.fragment.app.Fragment;

import org.warmbeachtides.tidegauge.R;

public class HomeFragment extends Fragment {

    private Handler mHandler;

    public View onCreateView(@NonNull LayoutInflater inflater, ViewGroup container, Bundle savedInstanceState) {
        View root = inflater.inflate(R.layout.fragment_page_home, container, false);
        
        mHandler = new Handler(Looper.getMainLooper());
        mStatusChecker.run();
        
        return root;
    }

    Runnable mStatusChecker = new Runnable() {
        @Override
        public void run() {
            try {
                Log.i("HOME FRAGMENT", "update");
            } finally {
                mHandler.postDelayed(mStatusChecker, 5000);
            }
        }
    };
}