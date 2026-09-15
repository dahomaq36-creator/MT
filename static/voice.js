let room = null;

let positionInterval = null;

let ownPosition = null;

let maxVoiceDistance = 80;

let fullVolumeDistance = 5;

const remoteAudio = new Map();


// =====================================================
// حساب المسافة بين لاعبين
// =====================================================

function getDistance(a, b) {

    if (!a || !b) {
        return Infinity;
    }

    const dx =
        Number(a.x) - Number(b.x);

    const dy =
        Number(a.y) - Number(b.y);

    const dz =
        Number(a.z) - Number(b.z);

    return Math.sqrt(
        dx * dx +
        dy * dy +
        dz * dz
    );
}


// =====================================================
// حساب مستوى الصوت
// =====================================================

function calculateVolume(distance) {

    if (!Number.isFinite(distance)) {
        return 0;
    }

    // أبعد من 80 = صامت
    if (distance >= maxVoiceDistance) {
        return 0;
    }

    // داخل 5 = صوت كامل
    if (distance <= fullVolumeDistance) {
        return 1;
    }

    const range =
        maxVoiceDistance -
        fullVolumeDistance;

    const position =
        (distance - fullVolumeDistance) /
        range;

    const volume =
        1 -
        Math.pow(position, 1.35);

    return Math.max(
        0,
        Math.min(1, volume)
    );
}


// =====================================================
// تحديث أصوات اللاعبين
// =====================================================

function updateAllAudioVolumes(players) {

    if (!room || !players || !ownPosition) {
        return;
    }

    for (
        const [identity, elements]
        of remoteAudio
    ) {

        let userId = null;

        if (
            identity.startsWith("roblox_")
        ) {
            userId =
                identity.substring(7);
        }

        if (!userId) {

            for (const element of elements) {
                element.volume = 0;
            }

            continue;
        }

        const remotePosition =
            players[userId];

        if (!remotePosition) {

            for (const element of elements) {
                element.volume = 0;
            }

            continue;
        }

        const distance =
            getDistance(
                ownPosition,
                remotePosition
            );

        const volume =
            calculateVolume(distance);

        for (const element of elements) {

            element.volume = volume;

        }
    }
}


// =====================================================
// جلب مواقع اللاعبين
// =====================================================

async function updatePositions() {

    if (!window.verifiedUserId) {
        return;
    }

    try {

        const response =
            await fetch(
                "/roblox/players",
                {
                    cache: "no-store"
                }
            );

        if (!response.ok) {
            return;
        }

        const players =
            await response.json();

        ownPosition =
            players[
                String(
                    window.verifiedUserId
                )
            ];

        if (!ownPosition) {

            updateAllAudioVolumes(
                players
            );

            return;
        }

        updateAllAudioVolumes(
            players
        );

    } catch (error) {

        console.error(
            "Position update error:",
            error
        );

    }
}


// =====================================================
// تشغيل تحديث المواقع
// =====================================================

function startPositionUpdates() {

    stopPositionUpdates();

    updatePositions();

    positionInterval =
        setInterval(
            updatePositions,
            500
        );
}


// =====================================================
// إيقاف تحديث المواقع
// =====================================================

function stopPositionUpdates() {

    if (positionInterval) {

        clearInterval(
            positionInterval
        );

        positionInterval = null;
    }
}


// =====================================================
// دخول الصوت
// =====================================================

async function connectVoice(userId) {

    const status =
        document.getElementById(
            "status"
        );

    try {

        status.textContent =
            "🎙️ جاري تشغيل المايك...";


        const response =
            await fetch(
                `/voice/token?user_id=${encodeURIComponent(userId)}`
            );


        const data =
            await response.json();


        if (!response.ok) {

            throw new Error(
                data.detail ||
                "فشل الحصول على توكن الصوت"
            );

        }


        maxVoiceDistance =
            Number(
                data.voice_max_distance || 80
            );


        fullVolumeDistance =
            Number(
                data.voice_full_volume_distance || 5
            );


        room =
            new LivekitClient.Room({
                adaptiveStream: true,
                dynacast: true
            });


        // =================================================
        // استقبال صوت لاعب
        // =================================================

        room.on(
            LivekitClient.RoomEvent.TrackSubscribed,
            (track, publication, participant) => {

                if (track.kind !== "audio") {
                    return;
                }


                const audio =
                    track.attach();


                audio.autoplay = true;

                audio.playsInline = true;


                audio.dataset.participantIdentity =
                    participant.identity;


                document.body.appendChild(
                    audio
                );


                if (
                    !remoteAudio.has(
                        participant.identity
                    )
                ) {

                    remoteAudio.set(
                        participant.identity,
                        new Set()
                    );

                }


                remoteAudio
                    .get(participant.identity)
                    .add(audio);


                updatePositions();

            }
        );


        // =================================================
        // إزالة صوت لاعب
        // =================================================

        room.on(
            LivekitClient.RoomEvent.TrackUnsubscribed,
            (track, publication, participant) => {

                const elements =
                    remoteAudio.get(
                        participant.identity
                    );


                if (elements) {

                    for (
                        const element
                        of elements
                    ) {

                        try {
                            element.remove();
                        } catch (_) {}

                    }

                    remoteAudio.delete(
                        participant.identity
                    );

                }


                try {
                    track.detach();
                } catch (_) {}

            }
        );


        // =================================================
        // الاتصال بـ LiveKit
        // =================================================

        await room.connect(
            data.url,
            data.token
        );


        // =================================================
        // تشغيل المايك
        // =================================================

        await room.localParticipant
            .setMicrophoneEnabled(true);


        status.textContent =
            "🟢 متصل بالصوت";


        startPositionUpdates();

    } catch (error) {

        console.error(error);

        status.textContent =
            "❌ " +
            (
                error.message ||
                "فشل الاتصال بالصوت"
            );


        stopPositionUpdates();

    }
}


// =====================================================
// خروج من الصوت
// =====================================================

async function disconnectVoice() {

    stopPositionUpdates();


    if (room) {

        try {

            await room.disconnect();

        } catch (_) {}

        room = null;

    }


    // حذف جميع أصوات اللاعبين

    for (
        const elements
        of remoteAudio.values()
    ) {

        for (
            const element
            of elements
        ) {

            try {
                element.remove();
            } catch (_) {}

        }

    }


    remoteAudio.clear();


    ownPosition = null;


    document.getElementById(
        "status"
    ).textContent =
        "🔴 غير متصل";
}
