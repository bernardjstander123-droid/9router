package com.btu.cinema

import android.app.Activity
import android.os.Bundle
import android.widget.TextView
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
        val status = TextView(this).apply { textSize = 18f; setPadding(32, 64, 32, 32); text = "BTU: starting hardware encode..." }
        setContentView(status)
        Thread {
            try {
                val dest = File(getExternalFilesDir(null), "btu_hardware_test.mp4")
                encode(dest)
                runOnUiThread { status.text = "BTU hardware MP4 generated: ${dest.absolutePath} (${dest.length()} bytes)" }
            } catch (e: Throwable) {
                Log.e(tag, "Encoding failed", e)
                runOnUiThread { status.text = "BTU encode failed: ${e.message}" }
            }
        }.start()
    }
    private fun encode(dest: File) {
        val width = 640
        val height = 360
        val fps = 30
        val format = MediaFormat.createVideoFormat(MediaFormat.MIMETYPE_VIDEO_AVC, width, height).apply {
            setInteger(MediaFormat.KEY_COLOR_FORMAT, MediaCodecInfo.CodecCapabilities.COLOR_FormatSurface)
            setInteger(MediaFormat.KEY_BIT_RATE, 1_500_000)
            setInteger(MediaFormat.KEY_FRAME_RATE, fps)
            setInteger(MediaFormat.KEY_I_FRAME_INTERVAL, 1)
            setInteger(MediaFormat.KEY_BITRATE_MODE, MediaCodecInfo.EncoderCapabilities.BITRATE_MODE_CBR)
        }
        val codecInfo = MediaCodecList(MediaCodecList.REGULAR_CODECS).codecInfos.firstOrNull {
            it.isEncoder && it.isHardwareAccelerated &&
                it.supportedTypes.any { type -> type.equals(MediaFormat.MIMETYPE_VIDEO_AVC, ignoreCase = true) }
        } ?: error("No hardware AVC encoder reported")
        Log.i(tag, "Selected codec: ${codecInfo.name} hardware=${codecInfo.isHardwareAccelerated}")
        val codec = MediaCodec.createByCodecName(codecInfo.name)
        var muxer: MediaMuxer? = null
        var eglDisplay = EGL14.EGL_NO_DISPLAY
        var eglContext = EGL14.EGL_NO_CONTEXT
        var eglSurface = EGL14.EGL_NO_SURFACE
        var inputSurface: Surface? = null
        try {
            codec.configure(format, null, null, MediaCodec.CONFIGURE_FLAG_ENCODE)
            inputSurface = codec.createInputSurface()
            codec.start()
            muxer = MediaMuxer(dest.absolutePath, MediaMuxer.OutputFormat.MUXER_OUTPUT_MPEG_4)
            eglDisplay = EGL14.eglGetDisplay(EGL14.EGL_DEFAULT_DISPLAY)
            check(eglDisplay != EGL14.EGL_NO_DISPLAY)
            check(EGL14.eglInitialize(eglDisplay, IntArray(2), 0, IntArray(2), 0))
            val attribs = intArrayOf(
                EGL14.EGL_RED_SIZE, 8, EGL14.EGL_GREEN_SIZE, 8,
                EGL14.EGL_BLUE_SIZE, 8, EGL14.EGL_RENDERABLE_TYPE, EGL14.EGL_OPENGL_ES2_BIT,
                EGL14.EGL_NONE
            )
            val configs = arrayOfNulls<android.opengl.EGLConfig>(1)
            val count = IntArray(1)
            check(EGL14.eglChooseConfig(eglDisplay, attribs, 0, configs, 0, 1, count, 0) && count[0] > 0)
            eglContext = EGL14.eglCreateContext(
                eglDisplay, configs[0], EGL14.EGL_NO_CONTEXT,
                intArrayOf(EGL14.EGL_CONTEXT_CLIENT_VERSION, 2, EGL14.EGL_NONE), 0
            )
            check(eglContext != EGL14.EGL_NO_CONTEXT)
            eglSurface = EGL14.eglCreateWindowSurface(
                eglDisplay, configs[0], inputSurface, intArrayOf(EGL14.EGL_NONE), 0
            )
            check(eglSurface != EGL14.EGL_NO_SURFACE)
            check(EGL14.eglMakeCurrent(eglDisplay, eglSurface, eglSurface, eglContext))
            GLES20.glViewport(0, 0, width, height)
            var track = -1
            var started = false
            var eos = false
            val info = MediaCodec.BufferInfo()
            fun drain(waitForEos: Boolean) {
                var idle = 0
                while (!eos) {
                    val index = codec.dequeueOutputBuffer(info, if (waitForEos) 10_000L else 0L)
                    when (index) {
                        MediaCodec.INFO_TRY_AGAIN_LATER -> {
                            if (!waitForEos || ++idle > 2000) {
                                if (waitForEos) error("Timed out draining encoder EOS")
                                break
                            }
                        }
                        MediaCodec.INFO_OUTPUT_FORMAT_CHANGED -> {
                            check(!started)
                            track = muxer!!.addTrack(codec.outputFormat)
                            muxer!!.start()
                            started = true
                        }
                        else -> if (index >= 0) {
                            idle = 0
                            val buffer = codec.getOutputBuffer(index) ?: error("Missing codec buffer")
                            if (info.size > 0) {
                                check(started)
                                buffer.position(info.offset)
                                buffer.limit(info.offset + info.size)
                                muxer!!.writeSampleData(track, buffer, info)
                            }
                            eos = (info.flags and MediaCodec.BUFFER_FLAG_END_OF_STREAM) != 0
                            codec.releaseOutputBuffer(index, false)
                        }
                    }
                }
            }
            for (i in 0 until 30) {
                val t = i / 29f
                GLES20.glClearColor(t, 0.15f, 1f - t, 1f)
                GLES20.glClear(GLES20.GL_COLOR_BUFFER_BIT)
                val pts = i.toLong() * 1_000_000_000L / fps
                EGLExt.eglPresentationTimeANDROID(eglDisplay, eglSurface, pts)
                check(EGL14.eglSwapBuffers(eglDisplay, eglSurface)) { "EGL swap failed: ${EGL14.eglGetError()}" }
                drain(false)
            }
            codec.signalEndOfInputStream()
            drain(true)
            Log.i(tag, "MP4 complete bytes=${dest.length()} frames=30 codec=${codecInfo.name}")
        } finally {
            if (eglDisplay != EGL14.EGL_NO_DISPLAY) {
                EGL14.eglMakeCurrent(eglDisplay, EGL14.EGL_NO_SURFACE, EGL14.EGL_NO_SURFACE, EGL14.EGL_NO_CONTEXT)
                if (eglSurface != EGL14.EGL_NO_SURFACE) EGL14.eglDestroySurface(eglDisplay, eglSurface)
                if (eglContext != EGL14.EGL_NO_CONTEXT) EGL14.eglDestroyContext(eglDisplay, eglContext)
                EGL14.eglTerminate(eglDisplay)
            }
            try { codec.stop() } catch (_: Exception) {}
            codec.release()
            inputSurface?.release()
            try { muxer?.stop() } catch (_: Exception) {}
            muxer?.release()
        }
    }
}
