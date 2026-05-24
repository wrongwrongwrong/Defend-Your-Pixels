import { CANVAS_W, CANVAS_H } from "../constants.js";
import { playBgm, playSfx } from "../audio.js";

const W = CANVAS_W, H = CANVAS_H;
const CX = W / 2;

const STORY_VIDEO_SRC = "assets/audio/Story_Video_audio.mp4";
const INTRO_TITLE_KEY = "intro_title";

/** @typedef {'start'|'video'|'done'} IntroPhase */

// ─── Scene ─────────────────────────────────────────────────────────────────

export class IntroScene extends Phaser.Scene {
  constructor() { super("Intro"); }

  init(data) {
    this.ws                 = data.ws;
    this._slideObjs         = [];
    /** @type {IntroPhase} */
    this._introPhase        = "start";
    this._inStartScreen     = false;
    this._inVideo           = false;
    this._startChoiceLocked = false;
    this._htmlVideo         = null;
    this._videoHostClick    = null;
    this._onVideoEnded      = null;
    this._onVideoError      = null;
    this._onVideoMetadata   = null;
    this._latestState       = null;
    this._audioStarted      = false;
    this._videoHint         = null;
    this._chosenMode        = null;
    this._cleanedUp         = false;
  }

  _cleanupScene() {
    if (this._cleanedUp) return;
    this._cleanedUp = true;
    this._teardownStoryVideo();
    this._setIntroStage(false);
    if (this.ws && this._stateHandler) {
      this.ws.off("state", this._stateHandler);
      this._stateHandler = null;
    }
    if (this._pointerAdvanceHandler) {
      this.input.off("pointerdown", this._pointerAdvanceHandler);
      this._pointerAdvanceHandler = null;
    }
    if (this._keyAdvanceHandler) {
      this.input.keyboard.off("keydown", this._keyAdvanceHandler);
      this._keyAdvanceHandler = null;
    }
  }

  create() {
    this._introPhase = "start";
    this._cleanedUp = false;
    this._setIntroStage(true);
    this.events.once("shutdown", this._cleanupScene, this);
    this.events.once("destroy", this._cleanupScene, this);

    this._pointerAdvanceHandler = () => {
      this._startAudio();
      if (this._inVideo) this._handleVideoAdvance();
    };
    this._keyAdvanceHandler = () => {
      this._startAudio();
      if (this._inVideo) this._handleVideoAdvance();
    };
    this.input.on("pointerdown", this._pointerAdvanceHandler);
    this.input.keyboard.on("keydown", this._keyAdvanceHandler);

    if (this.ws) {
      this._stateHandler = (s) => {
        this._latestState = s;
        if (s?.phase === "game") {
          this._teardownStoryVideo();
          this._goToGame(s);
        }
      };
      this.ws.on("state", this._stateHandler);
    }

    this._showStartScreen();
  }

  _setIntroStage(active) {
    document.body.classList.toggle("intro-stage", active);
    if (!active) {
      document.body.classList.remove("intro-video-playing");
    }
  }

  _finishIntro() {
    if (this._introPhase === "done") return;
    this._teardownStoryVideo();
    this._goToGame(this._latestState);
  }

  _startAudio() {
    if (this._audioStarted) return;
    this._audioStarted = true;
    if (this.sound.locked) this.sound.unlock();
    playBgm(this, "bgm_outback");
  }

  // ─── Start screen ─────────────────────────────────────────────────────────

  _showStartScreen() {
    this._teardownStoryVideo();
    this._introPhase = "start";
    this._setIntroStage(true);
    this._inStartScreen = true;
    this._startChoiceLocked = false;
    this._clearSlide();

    const objs = [];
    const titleY = H * 0.28;


    if (this.textures.exists(INTRO_TITLE_KEY)) {
      const img = this.add.image(CX, titleY, INTRO_TITLE_KEY);
      const maxW = W * 0.90;
      const maxH = H * 0.42;
      img.setScale(Math.min(maxW / img.width, maxH / img.height, 1));
      objs.push(img);
    } else {
      objs.push(this.add.text(CX, titleY - 16, "Old Mick and the Emus", {
        fontFamily: "'Press Start 2P', monospace",
        fontSize: "13px",
        color: "#d4a030",
        align: "center",
      }).setOrigin(0.5));
      objs.push(this.add.text(CX, titleY + 22, "Put Picture here", {
        fontFamily: "serif",
        fontSize: "15px",
        color: "#6a6a6a",
        align: "center",
      }).setOrigin(0.5));
    }

    const startBtn = this._makeActionButton(
      CX, H * 0.62, 280, 44,
      "START GAME", "#f0e060", 0x1a1208, 0xc8a030,
    );
    startBtn.bg.on("pointerdown", () => this._onStartGame());
    objs.push(startBtn.container);

    const tutBtn = this._makeActionButton(
      CX, H * 0.74, 280, 44,
      "TUTORIAL", "#a8e090", 0x0a1a10, 0x40a060,
    );
    tutBtn.bg.on("pointerdown", () => this._onTutorial());
    objs.push(tutBtn.container);

    objs.forEach(o => o.setAlpha(0));
    this.tweens.add({
      targets: objs,
      alpha: 1,
      duration: 600,
      delay: this.tweens.stagger(60),
    });

    this._slideObjs = objs;
  }

  _makeActionButton(x, y, w, h, label, textColor, bgColor, rimColor) {
    const container = this.add.container(x, y);

    const bg = this.add.rectangle(0, 0, w, h, bgColor)
      .setStrokeStyle(2, rimColor)
      .setInteractive({ useHandCursor: true });
    const txt = this.add.text(0, 0, label, {
      fontFamily: "'Press Start 2P', monospace",
      fontSize: "10px",
      color: textColor,
    }).setOrigin(0.5);

    bg.on("pointerover", () => bg.setFillStyle(rimColor));
    bg.on("pointerout", () => bg.setFillStyle(bgColor));

    container.add([bg, txt]);
    return { container, bg };
  }

  _onStartGame() {
    if (!this._inStartScreen || this._startChoiceLocked) return;
    this._startChoiceLocked = true;
    this._startAudio();
    playSfx(this, "sfx_select");
    this._chosenMode = "normal";
    this.ws?.send("select_mode", { mode: "normal" });
    this._fadeOutSlide(() => {
      this._inStartScreen = false;
      this._introPhase = "video";
      this._showStoryVideo(true);
    });
  }

  _onTutorial() {
    if (!this._inStartScreen || this._startChoiceLocked) return;
    this._startChoiceLocked = true;
    this._startAudio();
    playSfx(this, "sfx_select");
    this._chosenMode = "tutorial";
    this.ws?.send("select_mode", { mode: "tutorial" });
    this._fadeOutSlide(() => {
      this._inStartScreen = false;
      this._finishIntro();
    });
  }

  // ─── Story video (HTML host in board-area) ────────────────────────────────

  _getVideoHost() {
    return document.getElementById("intro-video-host");
  }

  _applyVideoNativeSize(video) {
    const vw = video.videoWidth;
    const vh = video.videoHeight;
    if (!vw || !vh) return;
    video.width = vw;
    video.height = vh;
    video.style.width = `${vw}px`;
    video.style.height = `${vh}px`;
    video.style.maxWidth = "100%";
    video.style.maxHeight = "100%";
    video.style.objectFit = "none";
  }

  _showStoryVideo(autoplay = false) {
    this._teardownStoryVideo();
    this._inVideo = true;
    this._clearSlide();

    const host = this._getVideoHost();
    if (!host) {
      console.warn("[intro] intro-video-host missing");
      this._finishStoryVideo();
      return;
    }

    document.body.classList.add("intro-video-playing");
    host.innerHTML = "";
    host.classList.remove("hidden");
    host.setAttribute("aria-hidden", "false");

    const video = document.createElement("video");
    video.className = "intro-story-video";
    video.src = STORY_VIDEO_SRC;
    video.setAttribute("playsinline", "");
    video.preload = "auto";
    video.playsInline = true;
    this._htmlVideo = video;

    const skip = document.createElement("div");
    skip.className = "intro-video-skip";
    skip.textContent = "tap to play  ›";

    host.appendChild(video);
    host.appendChild(skip);

    this._onVideoMetadata = () => {
      this._applyVideoNativeSize(video);
      skip.textContent = video.paused || video.ended ? "tap to play  ›" : "tap to skip  ›";
    };
    this._onVideoEnded = () => this._finishStoryVideo();
    this._onVideoError = () => {
      console.warn("[intro] story video failed to load:", STORY_VIDEO_SRC);
      this._finishStoryVideo();
    };
    video.addEventListener("loadedmetadata", this._onVideoMetadata);
    video.addEventListener("ended", this._onVideoEnded);
    video.addEventListener("error", this._onVideoError);
    video.addEventListener("play", () => { skip.textContent = "tap to skip  ›"; });
    video.addEventListener("pause", () => {
      skip.textContent = video.ended ? "tap to skip  ›" : "tap to play  ›";
    });

    this._videoHostClick = () => this._handleVideoAdvance();
    host.addEventListener("click", this._videoHostClick);

    this._videoHint = this.add.text(CX, H - 55, "tap to play  ›", {
      fontFamily: "monospace", fontSize: "11px", color: "#d4a030",
    }).setOrigin(0.5).setDepth(11);
    this.tweens.add({
      targets: this._videoHint, alpha: 1, duration: 600,
      yoyo: true, repeat: -1, ease: "Sine.easeInOut",
    });

    if (autoplay) {
      video.play().catch(() => this._finishStoryVideo());
    }
  }

  _handleVideoAdvance() {
    const video = this._htmlVideo;
    if (!video) {
      this._finishStoryVideo();
      return;
    }
    if (video.paused || video.ended) {
      video.play().catch(() => this._finishStoryVideo());
      return;
    }
    this._finishStoryVideo();
  }

  _teardownStoryVideo() {
    const host = this._getVideoHost();
    const video = this._htmlVideo;
    if (video) {
      if (this._onVideoEnded) video.removeEventListener("ended", this._onVideoEnded);
      if (this._onVideoError) video.removeEventListener("error", this._onVideoError);
      if (this._onVideoMetadata) video.removeEventListener("loadedmetadata", this._onVideoMetadata);
      video.pause();
      try {
        video.removeAttribute("src");
        video.load();
      } catch (_) { /* ignore */ }
    }
    if (host && this._videoHostClick) {
      host.removeEventListener("click", this._videoHostClick);
    }
    if (host) {
      host.innerHTML = "";
      host.classList.add("hidden");
      host.setAttribute("aria-hidden", "true");
    }
    document.body.classList.remove("intro-video-playing");
    this._htmlVideo = null;
    this._videoHostClick = null;
    this._onVideoEnded = null;
    this._onVideoError = null;
    this._onVideoMetadata = null;
    this._videoHint?.destroy();
    this._videoHint = null;
    this._inVideo = false;
  }

  _finishStoryVideo() {
    if (this._introPhase !== "video") return;
    this._teardownStoryVideo();
    this._finishIntro();
  }

  _clearSlide() {
    this._slideObjs.forEach(o => o.destroy());
    this._slideObjs = [];
  }

  _fadeOutSlide(onDone) {
    if (!this._slideObjs.length) { onDone?.(); return; }
    this.tweens.add({
      targets: this._slideObjs, alpha: 0, duration: 350,
      onComplete: () => { this._clearSlide(); onDone?.(); },
    });
  }

  _goToGame(initialState) {
    if (this._introPhase === "done") return;
    this._introPhase = "done";
    this._cleanupScene();
    this.cameras.main.fadeOut(400, 10, 8, 4);
    this.cameras.main.once("camerafadeoutcomplete", () => {
      this.scene.start("Game", { ws: this.ws, initialState });
    });
  }
}
