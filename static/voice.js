let room = null;

async function connectVoice(userId) {
    const status = document.getElementById("status");

    try {
        status.textContent = "جاري الاتصال...";

        const response = await fetch(
            `/voice/token?user_id=${encodeURIComponent(userId)}`
        );

        if (!response.ok) {
            throw new Error("Token request failed");
        }

        const data = await response.json();

        room = new LivekitClient.Room();

        room.on(
            LivekitClient.RoomEvent.TrackSubscribed,
            (track) => {
                if (track.kind === "audio") {
                    const audio = track.attach();
                    document.body.appendChild(audio);
                }
            }
        );

        await room.connect(data.url, data.token);

        await room.localParticipant.setMicrophoneEnabled(true);

        status.textContent = "🟢 متصل بالصوت";
    } catch (error) {
        console.error(error);
        status.textContent = "❌ فشل الاتصال";
    }
}

async function disconnectVoice() {
    if (room) {
        await room.disconnect();
        room = null;
    }

    document.getElementById("status").textContent = "🔴 غير متصل";
}
