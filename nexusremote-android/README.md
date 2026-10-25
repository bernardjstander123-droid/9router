# NexusRemote — Android app

This is a compiled native Android application that embeds only the HTTPS NexusRemote web portal at https://nexusremote-operations.vercel.app. It is NOT a fully offline call-center or independent dialer.

Features:
- Launch Home, Apply, Worker and Owner from native tabs.
- Check the real server health and identify whether Stripe, WhatsApp or dialer integrations are active.
- Owner and worker access remain protected by the deployed backend.
- No credentials embedded, no SMS/contact/microphone/camera/location permissions.
- External domains open in the system browser; HTTPS only in WebView.
- Android 8+.

Building: Use Java 17, Gradle 8.10.2, Android SDK 35 and run `gradle :app:assembleDebug --no-daemon` inside `nexusremote-android/`. Installable debug APK at `app/build/outputs/apk/debug/app-debug.apk`. Debug-signed for sideload testing; not an official app-store release.

Important:
- Recruitment and worker access cannot be fully active before a real employer, consent, approved workers, professional email domain and legitimate campaigns.
- No live Stripe payments, worker payouts or WhatsApp alerts are claimed; these require explicit provider activation and testing.
- The public website is hosted on Vercel and storage is private.
