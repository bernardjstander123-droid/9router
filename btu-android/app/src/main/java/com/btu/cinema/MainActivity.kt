package com.btu.cinema

import android.app.Activity
import android.os.Bundle
import android.widget.TextView
import android.widget.VideoView
import android.widget.Button
import android.widget.LinearLayout
import android.view.ViewGroup
import android.widget.Button
import android.widget.LinearLayout
import android.widget.VideoView
import android.view.ViewGroup
import android.util.Log
import android.media.MediaCodec
import android.media.MediaCodecInfo
import android.media.MediaCodecList
import android.media.MediaFormat
import android.media.MediaMuxer
import android.opengl.EGL14
import android.opengl.EGLExt
import android.opengl.GLES20
import android.view.Surface
import java.io.File

class MainActivity : Activity() {
    private val tag = "BTU_Engine_Audit"
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val layout = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(28, 48, 28, 28)
        }
        val layout = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(20, 40, 20, 20)
        }
        val status = TextView(this).apply {
            textSize = 18f
            text = "BTU: starting hardware encode..."
        }
        val video = VideoView(this)
        val replay = Button(this).apply {
            text = "Replay video"
            isEnabled = false
            setOnClickListener { video.seekTo(0); video.start() }
        }
        layout.addView(status)
        layout.addView(video, LinearLayout.LayoutParams(
            ViewGroup.LayoutParams.MATCH_PARENT, 0, 1f
        ))
        layout.addView(replay)
        setContentView(layout)
        Thread {
            try {
                val dest = File(getExternalFilesDir(null), "btu_hardware_test.mp4")
                encode(dest)
                check(dest.length() > 0L) { "Empty MP4 output" }
                runOnUiThread {
                    status.text = "BTU hardware test: ${dest.length()} bytes. Tap video to pause/play."
                    video.setVideoPath(dest.absolutePath)
                    video.setOnPreparedListener {
                        replay.isEnabled = true
                        video.start()
                    }
                    video.setOnErrorListener { _, what, extra ->
                        status.text = "Video playback failed (what=$what, extra=$extra)"
                        true
                    }
                    video.setOnClickListener {
                        if (video.isPlaying) video.pause() else video.start()
                    }
                }
            } catch (e: Throwable) {
                Log.e(tag, "Encoding failed", e)
                runOnUiThread { status.text = "BTU encode failed: ${e.message}" }
            }
        }.start()
    }

