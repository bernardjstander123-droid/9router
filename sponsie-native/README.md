# Sponsie Autopilot Native Android MVP

This standalone offline Android application is a small, original native companion to the existing Termux-hosted Sponsie Python suite. It is **not** that Python runtime bundled inside an APK. It does not execute local LLM inference and does not connect to n8n, Custom GPT Actions, external job boards or Cerebrium.

Features implemented: mobile dashboard, native persistent SQLite project/approval history, draft generation for HTML landing pages, proposals, research ledgers and content, manual Android share/export of draft text, owner confirmation before marking a draft ready. There are no client data collectors, paid API keys, background account connections, automatic messages, contracts or payment flows. All generated drafts carry explicit warnings. No Internet permission.

Build (Java 17 and Android SDK 35): `gradle :app:assembleDebug --no-daemon` in this directory. For GitHub CI copy this directory to `sponsie-native/` and add supplied workflow. Install `app/build/outputs/apk/debug/app-debug.apk` from GitHub Actions artifacts after verifying SHA-256.

The debug APK is signed with Android's development key and is **not** a Play Store release. Install only for personal device testing. No device test has been performed unless explicitly verified on device.
