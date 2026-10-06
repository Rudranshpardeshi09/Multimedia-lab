/*
 * Task 04: Voice Transformer — Web UI
 * Multimedia Systems Laboratory
 * Author: Rudranshpardeshi09
 *
 * Vanilla-JS port of the "Retone" Next.js client. A single state machine
 * (idle -> recording -> source-ready -> processing -> result-ready | error)
 * drives a re-render of the source panel; high-frequency updates (recording
 * timer, level meter, processing clock) patch the DOM in place.
 */
(function () {
  "use strict";

  // ------------------------------------------------------------------ consts

  var CONFIG_ENDPOINT = "/api/config";
  var CONVERT_ENDPOINT = "/api/convert";
  var RECOMMENDED_RANGE = { min: 5, max: 15 };
  var RECORDING_MIME_CANDIDATES = [
    "audio/webm;codecs=opus",
    "audio/ogg;codecs=opus",
    "audio/webm",
    "audio/mp4",
    "audio/ogg",
  ];
  var TIMER_INTERVAL_MS = 100;
  var BAR_COUNT = 40;
  var REDUCED_MOTION_FPS = 6;

  // Environment variables the server reads; shown in the setup checklist.
  var SETUP_API_KEY_VAR = "ELEVENLABS_API_KEY";
  var SETUP_VOICE_VARS = [
    { name: "Warm Narrator", variable: "ELEVENLABS_VOICE_WARM_ID" },
    { name: "Deep Studio", variable: "ELEVENLABS_VOICE_DEEP_ID" },
    { name: "Bright Conversational", variable: "ELEVENLABS_VOICE_BRIGHT_ID" },
  ];

  var STEPS = [
    { id: "preparing", label: "Preparing audio" },
    { id: "transforming", label: "Transforming voice" },
    { id: "finalizing", label: "Finalizing result" },
  ];

  var ERROR_TITLES = {
    "quota-exhausted": "Demo usage limit reached",
    "rate-limited": "The voice service is busy",
    "audio-too-long": "Recording is too long",
    "file-too-large": "File is too large",
    "unsupported-format": "Unsupported audio",
    "invalid-audio": "Audio couldn't be processed",
    "empty-file": "Empty file",
    "missing-audio": "No audio received",
    "invalid-voice": "Choose a target voice",
    "provider-not-configured": "Voice service not configured",
    "provider-auth": "Voice service configuration problem",
    "provider-permission": "Voice service configuration problem",
    "provider-plan-required": "Target voice not available on this plan",
    "provider-voice-missing": "Target voice unavailable",
    "provider-timeout": "The voice service timed out",
    "provider-error": "The voice service had a problem",
    network: "Connection problem",
  };

  var VALIDATION_TITLES = {
    "empty-file": "Empty file",
    "file-too-large": "File is too large",
    "unsupported-format": "Unsupported audio format",
    "audio-too-long": "Recording is too long",
  };

  var REDUCED_MOTION = !!(window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches);

  // ------------------------------------------------------------------- icons

  var ICON_PATHS = {
    mic: '<rect x="9" y="3" width="6" height="11" rx="3"/><path d="M5 11a7 7 0 0 0 14 0"/><path d="M12 18v3"/><path d="M9 21h6"/>',
    stop: '<rect x="6" y="6" width="12" height="12" rx="2" fill="currentColor" stroke="none"/>',
    upload: '<path d="M12 16V4"/><path d="m7 9 5-5 5 5"/><path d="M4 16v3a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-3"/>',
    download: '<path d="M12 4v12"/><path d="m7 11 5 5 5-5"/><path d="M4 17v2a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-2"/>',
    sparkles:
      '<path d="M12 3v4"/><path d="M12 17v4"/><path d="M3 12h4"/><path d="M17 12h4"/><path d="m5.6 5.6 2.8 2.8"/><path d="m15.6 15.6 2.8 2.8"/><path d="m5.6 18.4 2.8-2.8"/><path d="m15.6 8.4 2.8-2.8"/>',
    refresh: '<path d="M20 12a8 8 0 1 1-2.34-5.66"/><path d="M20 4v5h-5"/>',
    trash: '<path d="M4 7h16"/><path d="M10 11v6"/><path d="M14 11v6"/><path d="M6 7l1 13h10l1-13"/><path d="M9 7V4h6v3"/>',
    check: '<path d="m5 12 4 4L19 6"/>',
    alert:
      '<path d="M12 9v4"/><path d="M12 17h.01"/><path d="M10.3 3.9 2.6 17.2A2 2 0 0 0 4.3 20h15.4a2 2 0 0 0 1.7-2.8L13.7 3.9a2 2 0 0 0-3.4 0Z"/>',
    info: '<circle cx="12" cy="12" r="9"/><path d="M12 11v5"/><path d="M12 8h.01"/>',
    spinner: '<path d="M12 3a9 9 0 1 0 9 9"/>',
    wave: '<path d="M3 12h2"/><path d="M7 8v8"/><path d="M11 5v14"/><path d="M15 8v8"/><path d="M19 10v4"/>',
  };

  function icon(name, size, strokeWidth) {
    var svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    var px = String(size || 20);
    svg.setAttribute("width", px);
    svg.setAttribute("height", px);
    svg.setAttribute("viewBox", "0 0 24 24");
    svg.setAttribute("fill", "none");
    svg.setAttribute("stroke", "currentColor");
    svg.setAttribute("stroke-width", String(strokeWidth || 1.75));
    svg.setAttribute("stroke-linecap", "round");
    svg.setAttribute("stroke-linejoin", "round");
    svg.setAttribute("aria-hidden", "true");
    svg.setAttribute("focusable", "false");
    if (name === "spinner") svg.setAttribute("class", "spin");
    svg.innerHTML = ICON_PATHS[name] || ""; // static, trusted markup only
    return svg;
  }

  // ------------------------------------------------------------- dom helper

  /**
   * Tiny element factory. Strings become text nodes (never HTML), so file
   * names and server messages can be rendered safely.
   */
  function h(tag, props) {
    var el = document.createElement(tag);
    var children = Array.prototype.slice.call(arguments, 2);
    if (props) {
      Object.keys(props).forEach(function (key) {
        var value = props[key];
        if (value === null || value === undefined || value === false) return;
        if (key === "class") el.className = value;
        else if (key.slice(0, 2) === "on" && typeof value === "function") {
          el.addEventListener(key.slice(2).toLowerCase(), value);
        } else if (key === "disabled" || key === "checked" || key === "hidden" || key === "open") {
          el[key] = !!value;
        } else if (key === "ref") value(el);
        else el.setAttribute(key, value === true ? "" : String(value));
      });
    }
    appendChildren(el, children);
    return el;
  }

  function appendChildren(el, children) {
    children.forEach(function (child) {
      if (child === null || child === undefined || child === false) return;
      if (Array.isArray(child)) appendChildren(el, child);
      else if (child instanceof Node) el.appendChild(child);
      else el.appendChild(document.createTextNode(String(child)));
    });
  }

  function button(opts, label) {
    var cls = "btn btn-" + (opts.variant || "primary") + (opts.size === "lg" ? " btn-lg" : "");
    if (opts.className) cls += " " + opts.className;
    return h(
      "button",
      {
        type: "button",
        class: cls,
        disabled: opts.disabled,
        "data-key": opts.key,
        "aria-describedby": opts.describedBy,
        onClick: opts.onClick,
      },
      opts.icon ? opts.icon : null,
      label
    );
  }

  function clear(el) {
    while (el.firstChild) el.removeChild(el.firstChild);
  }

  // ------------------------------------------------------------- formatting

  function formatClock(totalSeconds) {
    var clamped = Math.max(0, Math.floor(totalSeconds));
    var m = Math.floor(clamped / 60);
    var s = clamped % 60;
    return (m < 10 ? "0" : "") + m + ":" + (s < 10 ? "0" : "") + s;
  }

  function formatDurationHuman(seconds) {
    if (!isFinite(seconds) || seconds < 0) return "an unknown length";
    if (seconds < 60) {
      var rounded = Math.round(seconds * 10) / 10;
      var text = rounded % 1 === 0 ? String(rounded) : rounded.toFixed(1);
      return text + " second" + (rounded === 1 ? "" : "s");
    }
    return Math.floor(seconds / 60) + " min " + Math.round(seconds % 60) + " sec";
  }

  function formatBytes(bytes) {
    if (bytes < 1024) return bytes + " B";
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(0) + " KB";
    return (bytes / (1024 * 1024)).toFixed(1) + " MB";
  }

  function buildDownloadFileName(date) {
    var d = date || new Date();
    var pad = function (n) {
      return (n < 10 ? "0" : "") + n;
    };
    return (
      "voice-conversion-" +
      d.getFullYear() + "-" + pad(d.getMonth() + 1) + "-" + pad(d.getDate()) + "-" +
      pad(d.getHours()) + pad(d.getMinutes()) + ".mp3"
    );
  }

  function extensionForMimeType(mimeType) {
    var base = (mimeType || "").split(";")[0].trim().toLowerCase();
    if (base.indexOf("webm") !== -1) return "webm";
    if (base.indexOf("ogg") !== -1) return "ogg";
    if (base.indexOf("mp4") !== -1 || base.indexOf("m4a") !== -1 || base.indexOf("aac") !== -1) return "m4a";
    if (base.indexOf("wav") !== -1) return "wav";
    if (base.indexOf("mpeg") !== -1 || base.indexOf("mp3") !== -1) return "mp3";
    return "webm";
  }

  // ------------------------------------------------------------- validation

  function normalizeMimeType(type) {
    return (type || "").split(";")[0].trim().toLowerCase();
  }

  function getFileExtension(name) {
    var trimmed = (name || "").trim();
    var dot = trimmed.lastIndexOf(".");
    if (dot === -1 || dot === trimmed.length - 1) return "";
    return trimmed.slice(dot + 1).toLowerCase();
  }

  function formatLabels() {
    var seen = [];
    config.formats.forEach(function (f) {
      if (seen.indexOf(f.label) === -1) seen.push(f.label);
    });
    return seen;
  }

  function acceptAttribute() {
    var items = [];
    config.formats.forEach(function (f) {
      [("." + f.extension)].concat(f.mime_types || []).forEach(function (item) {
        if (items.indexOf(item) === -1) items.push(item);
      });
    });
    return items.join(",");
  }

  // Extension or MIME type is enough here; the server checks the real
  // container before spending provider credits.
  function isSupportedAudio(file) {
    var ext = getFileExtension(file.name);
    var mime = normalizeMimeType(file.type);
    return config.formats.some(function (f) {
      return f.extension === ext || (f.mime_types || []).indexOf(mime) !== -1;
    });
  }

  function validateAudioFile(file) {
    if (file.size <= 0) {
      return { ok: false, code: "empty-file", message: "This file is empty. Please choose a recording that contains audio." };
    }
    if (file.size > limits.maxSizeBytes) {
      return {
        ok: false,
        code: "file-too-large",
        message:
          "This file is too large (" + formatBytes(file.size) + "). The maximum is " + formatBytes(limits.maxSizeBytes) + ".",
      };
    }
    if (!isSupportedAudio(file)) {
      return {
        ok: false,
        code: "unsupported-format",
        message: "This audio format is not supported. Please use " + formatLabels().join(", ") + ".",
      };
    }
    return { ok: true };
  }

  function validateAudioDuration(seconds) {
    if (!isFinite(seconds) || seconds <= 0) {
      return {
        ok: false,
        code: "audio-too-long",
        message: "We couldn't determine how long this audio is. Try exporting it as MP3 or WAV and upload it again.",
      };
    }
    if (seconds > limits.maxDurationSeconds) {
      return {
        ok: false,
        code: "audio-too-long",
        message:
          "This recording is " + formatDurationHuman(seconds) + " long. The MVP currently supports up to " +
          limits.maxDurationSeconds + " seconds.",
      };
    }
    return { ok: true };
  }

  // Chrome reports Infinity for WebM blobs without a duration header. Seeking
  // far past the end makes it scan the file and emit durationchange.
  function getAudioDuration(blob, timeoutMs) {
    return new Promise(function (resolve, reject) {
      var audio = document.createElement("audio");
      audio.preload = "metadata";
      audio.muted = true;
      var url = URL.createObjectURL(blob);
      var settled = false;
      var nudged = false;
      var timer = window.setTimeout(function () {
        finish(null, new Error("Timed out while reading the audio duration."));
      }, timeoutMs || 10000);

      function finish(duration, error) {
        if (settled) return;
        settled = true;
        window.clearTimeout(timer);
        audio.removeEventListener("loadedmetadata", onMetadata);
        audio.removeEventListener("durationchange", onDurationChange);
        audio.removeEventListener("error", onError);
        audio.removeAttribute("src");
        audio.load();
        URL.revokeObjectURL(url);
        if (error) reject(error);
        else resolve(duration);
      }
      function settleIfFinite() {
        if (isFinite(audio.duration) && audio.duration > 0) {
          finish(audio.duration);
          return true;
        }
        return false;
      }
      function onMetadata() {
        if (settleIfFinite()) return;
        if (!nudged) {
          nudged = true;
          audio.currentTime = Number.MAX_SAFE_INTEGER;
        }
      }
      function onDurationChange() {
        settleIfFinite();
      }
      function onError() {
        finish(null, new Error("The browser could not decode this audio file."));
      }
      audio.addEventListener("loadedmetadata", onMetadata);
      audio.addEventListener("durationchange", onDurationChange);
      audio.addEventListener("error", onError);
      audio.src = url;
    });
  }

  // ------------------------------------------------------- microphone errors

  var RECORDING_UNSUPPORTED_ERROR = {
    code: "recording-unsupported",
    title: "Recording isn't supported in this browser",
    message:
      "Try a recent version of Chrome, Edge, Firefox or Safari — or switch to Upload and choose an audio file instead.",
  };

  function describeMicrophoneError(error) {
    var name = error && typeof error === "object" && "name" in error ? String(error.name) : "";
    switch (name) {
      case "NotAllowedError":
      case "PermissionDeniedError":
        return {
          code: "microphone-denied",
          title: "Microphone access was blocked",
          message:
            "Allow microphone access for this site in your browser settings, then press Record again. You can also upload a file instead.",
        };
      case "NotFoundError":
      case "DevicesNotFoundError":
        return {
          code: "microphone-not-found",
          title: "No microphone found",
          message: "Connect a microphone (or check your system's input settings) and try again, or upload an audio file.",
        };
      case "NotReadableError":
      case "TrackStartError":
      case "AbortError":
        return {
          code: "microphone-unavailable",
          title: "Microphone is unavailable",
          message: "Another application may be using your microphone. Close it and try again, or upload an audio file.",
        };
      case "SecurityError":
        return {
          code: "microphone-insecure",
          title: "Microphone requires a secure connection",
          message:
            "Recording only works over HTTPS or on localhost. Open the site over a secure connection or upload a file.",
        };
      case "OverconstrainedError":
        return {
          code: "microphone-constraints",
          title: "Microphone settings unsupported",
          message:
            "Your microphone doesn't support the requested settings. Try a different input device or upload a file.",
        };
      default:
        return {
          code: "microphone-error",
          title: "Recording couldn't start",
          message:
            "Something prevented the microphone from starting. Reload the page and try again, or upload a file instead.",
        };
    }
  }

  function isRecordingSupported() {
    return (
      typeof window.MediaRecorder === "function" &&
      !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia)
    );
  }

  function pickRecordingMimeType() {
    if (typeof MediaRecorder === "undefined" || typeof MediaRecorder.isTypeSupported !== "function") return undefined;
    for (var i = 0; i < RECORDING_MIME_CANDIDATES.length; i += 1) {
      if (MediaRecorder.isTypeSupported(RECORDING_MIME_CANDIDATES[i])) return RECORDING_MIME_CANDIDATES[i];
    }
    return undefined;
  }

  // ---------------------------------------------------------------- recorder

  var rec = {
    status: "idle", // idle | requesting | recording | stopping
    elapsedMs: 0,
    analyser: null,
    mediaRecorder: null,
    stream: null,
    context: null,
    chunks: [],
    startedAt: 0,
    timer: null,
    cancelled: false,
    busy: false,
  };

  function recSetStatus(status) {
    rec.status = status;
    render();
  }

  function recRelease() {
    if (rec.timer !== null) {
      window.clearInterval(rec.timer);
      rec.timer = null;
    }
    if (rec.stream) rec.stream.getTracks().forEach(function (t) { t.stop(); });
    rec.stream = null;
    var ctx = rec.context;
    rec.context = null;
    if (ctx && ctx.state !== "closed") ctx.close().catch(function () {});
    rec.mediaRecorder = null;
    rec.analyser = null;
    rec.busy = false;
    stopVisualizer();
  }

  function recStop() {
    var mr = rec.mediaRecorder;
    if (!mr || mr.state === "inactive") return;
    recSetStatus("stopping");
    mr.stop();
  }

  function recCancel() {
    rec.cancelled = true;
    var mr = rec.mediaRecorder;
    if (mr && mr.state !== "inactive") mr.stop();
    else recRelease();
    rec.elapsedMs = 0;
    rec.status = "idle";
    dispatch({ type: "recording-cancelled" });
  }

  function recAttachAnalyser(stream) {
    try {
      var Ctor = window.AudioContext || window.webkitAudioContext;
      if (!Ctor) return;
      var ctx = new Ctor();
      var source = ctx.createMediaStreamSource(stream);
      var node = ctx.createAnalyser();
      node.fftSize = 256;
      node.smoothingTimeConstant = 0.8;
      source.connect(node);
      rec.context = ctx;
      rec.analyser = node;
    } catch (e) {
      // The level meter is optional; recording continues without it.
    }
  }

  function recStart() {
    if (rec.busy) return;
    if (!isRecordingSupported()) {
      dispatch({ type: "failed", error: RECORDING_UNSUPPORTED_ERROR });
      return;
    }
    rec.busy = true;
    rec.cancelled = false;
    recSetStatus("requesting");

    navigator.mediaDevices
      .getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true } })
      .then(
        function (stream) {
          if (rec.cancelled) {
            stream.getTracks().forEach(function (t) { t.stop(); });
            rec.busy = false;
            return;
          }
          rec.stream = stream;
          var preferred = pickRecordingMimeType();
          var mr;
          try {
            mr = preferred ? new MediaRecorder(stream, { mimeType: preferred }) : new MediaRecorder(stream);
          } catch (err) {
            recRelease();
            rec.status = "idle";
            dispatch({ type: "failed", error: describeMicrophoneError(err) });
            return;
          }
          rec.mediaRecorder = mr;
          rec.chunks = [];
          recAttachAnalyser(stream);

          mr.ondataavailable = function (event) {
            if (event.data && event.data.size > 0) rec.chunks.push(event.data);
          };
          mr.onerror = function () {
            recRelease();
            rec.status = "idle";
            rec.elapsedMs = 0;
            dispatch({
              type: "failed",
              error: {
                code: "recording-failed",
                title: "Recording failed",
                message: "The browser stopped the recording unexpectedly. Please try again.",
              },
            });
          };
          mr.onstart = function () {
            rec.startedAt = performance.now();
            rec.elapsedMs = 0;
            rec.status = "recording";
            pendingFocus = "rec-stop";
            dispatch({ type: "recording-started" });
            rec.timer = window.setInterval(function () {
              var elapsed = performance.now() - rec.startedAt;
              rec.elapsedMs = Math.min(elapsed, limits.maxDurationSeconds * 1000);
              updateRecordingClock();
              if (elapsed >= limits.maxDurationSeconds * 1000) recStop();
            }, TIMER_INTERVAL_MS);
          };
          mr.onstop = function () {
            var elapsedAtStop = performance.now() - rec.startedAt;
            var mime = mr.mimeType || preferred || "audio/webm";
            var blob = new Blob(rec.chunks, { type: mime });
            rec.chunks = [];
            var wasCancelled = rec.cancelled;
            recRelease();
            rec.status = "idle";
            rec.elapsedMs = 0;
            if (wasCancelled) {
              render();
              return;
            }
            if (blob.size === 0) {
              dispatch({
                type: "failed",
                error: {
                  code: "recording-empty",
                  title: "Nothing was recorded",
                  message: "The recording came back empty. Check that your microphone is working and try again.",
                },
              });
              return;
            }
            acceptSource({
              blob: blob,
              durationSeconds: Math.min(elapsedAtStop, limits.maxDurationSeconds * 1000) / 1000,
              mimeType: mime,
              fileName: "recording." + extensionForMimeType(mime),
              origin: "recording",
            });
          };
          mr.start();
        },
        function (err) {
          rec.busy = false;
          rec.status = "idle";
          if (rec.cancelled) {
            render();
            return;
          }
          dispatch({ type: "failed", error: describeMicrophoneError(err) });
        }
      );
  }

  function updateRecordingClock() {
    var elapsed = rec.elapsedMs / 1000;
    var remaining = Math.max(0, limits.maxDurationSeconds - elapsed);
    var clock = document.getElementById("rec-clock");
    if (clock) clock.textContent = formatClock(elapsed);
    var hint = document.getElementById("rec-hint");
    if (hint) {
      hint.textContent =
        remaining <= 5
          ? "Stopping automatically in " + Math.ceil(remaining) + "s."
          : "Stops automatically at " + limits.maxDurationSeconds + " seconds.";
    }
  }

  // ------------------------------------------------------------- visualizer

  var viz = { frame: 0, canvas: null, data: null, lastDraw: 0 };

  function startVisualizer(canvas) {
    stopVisualizer();
    viz.canvas = canvas;
    viz.data = rec.analyser ? new Uint8Array(rec.analyser.frequencyBinCount) : null;
    viz.lastDraw = 0;
    viz.frame = window.requestAnimationFrame(drawVisualizer);
  }

  function stopVisualizer() {
    if (viz.frame) window.cancelAnimationFrame(viz.frame);
    viz.frame = 0;
    viz.canvas = null;
  }

  function drawVisualizer(now) {
    var canvas = viz.canvas;
    if (!canvas || !canvas.isConnected) {
      viz.frame = 0;
      return;
    }
    viz.frame = window.requestAnimationFrame(drawVisualizer);
    if (REDUCED_MOTION && now - viz.lastDraw < 1000 / REDUCED_MOTION_FPS) return;
    viz.lastDraw = now;

    var ctx = canvas.getContext("2d");
    if (!ctx) return;
    var ratio = window.devicePixelRatio || 1;
    var width = canvas.clientWidth;
    var height = canvas.clientHeight;
    if (canvas.width !== Math.round(width * ratio) || canvas.height !== Math.round(height * ratio)) {
      canvas.width = Math.round(width * ratio);
      canvas.height = Math.round(height * ratio);
    }
    ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
    ctx.clearRect(0, 0, width, height);
    ctx.fillStyle = getComputedStyle(canvas).color;

    var gap = 3;
    var barWidth = Math.max(2, (width - gap * (BAR_COUNT - 1)) / BAR_COUNT);
    var minHeight = 3;
    var data = viz.data;
    if (rec.analyser && data) rec.analyser.getByteFrequencyData(data);
    var sum = 0;
    for (var i = 0; i < BAR_COUNT; i += 1) {
      // Sample lower frequencies more densely; that is where speech lives.
      var bin = data ? Math.floor(Math.pow(i / BAR_COUNT, 1.6) * data.length * 0.6) : 0;
      var level = data ? data[bin] / 255 : 0;
      sum += level;
      var barHeight = minHeight + level * (height - minHeight);
      var x = i * (barWidth + gap);
      var y = (height - barHeight) / 2;
      ctx.beginPath();
      if (typeof ctx.roundRect === "function") ctx.roundRect(x, y, barWidth, barHeight, barWidth / 2);
      else ctx.rect(x, y, barWidth, barHeight);
      ctx.fill();
    }
    // Expose an approximate input level to assistive tech without chatter.
    canvas.setAttribute("data-level", String(Math.round((sum / BAR_COUNT) * 100)));
  }

  // ------------------------------------------------------------------ state

  var config = null;
  var limits = { maxDurationSeconds: 30, maxSizeBytes: 15 * 1024 * 1024 };
  var elevenVoices = []; // voices with a configured ElevenLabs voice ID
  var providerConfigured = false;
  var elevenReady = false;

  var state = { phase: "idle" };
  var mode = "record";
  var voiceSlug = null;
  var consentGiven = false;
  var uploadChecking = false;
  var abortController = null;
  var processingTimer = null;
  var pendingFocus = null;

  var objectUrls = [];
  function createUrl(blob) {
    var url = URL.createObjectURL(blob);
    objectUrls.push(url);
    return url;
  }
  function releaseUrl(url) {
    if (!url) return;
    URL.revokeObjectURL(url);
    var i = objectUrls.indexOf(url);
    if (i !== -1) objectUrls.splice(i, 1);
  }

  function currentSource() {
    return state.source || null;
  }

  function releaseCurrent() {
    var src = currentSource();
    if (src) releaseUrl(src.url);
    if (state.result) releaseUrl(state.result.url);
  }

  function reduce(s, action) {
    switch (action.type) {
      case "recording-started":
        return { phase: "recording" };
      case "recording-cancelled":
        return s.phase === "recording" ? { phase: "idle" } : s;
      case "source-ready":
        return { phase: "source-ready", source: action.source };
      case "discard-source":
      case "reset":
        return { phase: "idle" };
      case "processing-started":
        if (!s.source || s.phase === "processing") return s;
        return { phase: "processing", source: s.source, step: "preparing", startedAt: action.startedAt };
      case "processing-step":
        return s.phase === "processing"
          ? { phase: "processing", source: s.source, step: action.step, startedAt: s.startedAt }
          : s;
      case "processing-cancelled":
        return s.phase === "processing" ? { phase: "source-ready", source: s.source } : s;
      case "result-ready":
        return s.phase === "processing" ? { phase: "result-ready", source: s.source, result: action.result } : s;
      case "failed":
        return { phase: "error", source: s.source || null, error: action.error };
      case "retry":
        return s.phase === "error" && s.source ? { phase: "source-ready", source: s.source } : { phase: "idle" };
      default:
        return s;
    }
  }

  function dispatch(action) {
    var prev = state;
    state = reduce(state, action);
    if (state === prev) return;
    if (action.type === "processing-step") {
      updateProcessingSteps();
      return;
    }
    if (state.phase === "error") pendingFocus = "error-action";
    render();
  }

  function selectedVoice() {
    var list = elevenVoices;
    for (var i = 0; i < list.length; i += 1) if (list[i].slug === voiceSlug) return list[i];
    return list[0];
  }

  function acceptSource(source) {
    releaseCurrent();
    consentGiven = false;
    source.url = createUrl(source.blob);
    // Uploads must be confirmed first, so the Transform button starts disabled.
    pendingFocus = source.origin === "upload" ? "consent" : "transform";
    dispatch({ type: "source-ready", source: source });
  }

  function discardSource() {
    releaseCurrent();
    consentGiven = false;
    pendingFocus = mode === "record" ? "rec-start" : "upload-choose";
    dispatch({ type: "discard-source" });
  }

  function resetAll() {
    releaseCurrent();
    consentGiven = false;
    pendingFocus = mode === "record" ? "rec-start" : "upload-choose";
    dispatch({ type: "reset" });
  }

  function cancelProcessing() {
    if (abortController) abortController.abort();
    abortController = null;
    pendingFocus = "transform";
    dispatch({ type: "processing-cancelled" });
  }

  // ------------------------------------------------------------- api client

  function ClientError(code, message, status) {
    this.code = code;
    this.message = message;
    this.status = status === undefined ? null : status;
  }

  function toUserFacingError(error) {
    if (error instanceof ClientError) {
      return { code: error.code, title: ERROR_TITLES[error.code] || "Transformation failed", message: error.message };
    }
    return { code: "unexpected", title: "Something went wrong", message: "An unexpected error occurred. Please try again." };
  }

  function readNumberHeader(headers, name) {
    var value = headers.get(name);
    if (value === null) return null;
    var parsed = Number(value);
    return isFinite(parsed) ? parsed : null;
  }

  function errorFromResponse(response) {
    return response
      .text()
      .catch(function () {
        return "";
      })
      .then(function (text) {
        try {
          var body = JSON.parse(text);
          if (body && body.error && body.error.code && body.error.message) {
            return new ClientError(body.error.code, body.error.message, response.status);
          }
        } catch (e) {
          // Non-JSON body: something in front of the app rejected the request.
        }
        if (response.status === 413) {
          return new ClientError(
            "file-too-large",
            "This file is too large for the server to accept. Try a shorter recording or a compressed format such as MP3.",
            413
          );
        }
        if (response.status === 502 || response.status === 504) {
          return new ClientError(
            "provider-error",
            "The server did not respond in time. Please try again with a shorter recording.",
            response.status
          );
        }
        return new ClientError(
          "unexpected",
          "The server returned an unexpected response (" + response.status + "). Please try again.",
          response.status
        );
      });
  }

  function requestConversion(req) {
    req.onStep("preparing");
    var form = new FormData();
    form.append("audio", req.audio, req.fileName);
    form.append("voiceSlug", req.voiceSlug);

    req.onStep("transforming");
    return fetch(CONVERT_ENDPOINT, { method: "POST", body: form, signal: req.signal, cache: "no-store" })
      .catch(function (error) {
        if (error && error.name === "AbortError") throw new ClientError("aborted", "The transformation was cancelled.");
        throw new ClientError("network", "We couldn't reach the server. Check your internet connection and try again.");
      })
      .then(function (response) {
        if (!response.ok) {
          return errorFromResponse(response).then(function (err) {
            throw err;
          });
        }
        req.onStep("finalizing");
        return response.blob().then(function (blob) {
          if (blob.size === 0) {
            throw new ClientError("unexpected", "The server returned empty audio. Please try again.", response.status);
          }
          return {
            blob: blob.type ? blob : new Blob([blob], { type: "audio/mpeg" }),
            processingMs: readNumberHeader(response.headers, "X-Server-Ms"),
            providerMs: readNumberHeader(response.headers, "X-Provider-Ms"),
            sourceDuration: readNumberHeader(response.headers, "X-Source-Duration"),
          };
        });
      });
  }

  function transform() {
    var source = currentSource();
    if (!source || state.phase === "processing") return;
    if (source.origin === "upload" && !consentGiven) return;
    var controller = new AbortController();
    abortController = controller;
    var startedAt = performance.now();
    var voice = selectedVoice();
    pendingFocus = "cancel";
    dispatch({ type: "processing-started", startedAt: startedAt });

    requestConversion({
      audio: source.blob,
      fileName: source.fileName,
      voiceSlug: voice.slug,
      signal: controller.signal,
      onStep: function (step) {
        dispatch({ type: "processing-step", step: step });
      },
    })
      .then(function (res) {
        if (controller.signal.aborted) return;
        var roundTripMs = Math.round(performance.now() - startedAt);
        if (window.console && console.info) {
          console.info("[voice-transformer] conversion timing", {
            sourceSeconds: source.durationSeconds,
            sourceBytes: source.blob.size,
            outputBytes: res.blob.size,
            roundTripMs: roundTripMs,
            serverProcessingMs: res.processingMs,
            providerMs: res.providerMs,
          });
        }
        pendingFocus = "result-heading";
        dispatch({
          type: "result-ready",
          result: {
            blob: res.blob,
            url: createUrl(res.blob),
            downloadName: buildDownloadFileName(),
            processingMs: res.processingMs,
            providerMs: res.providerMs,
            roundTripMs: roundTripMs,
            voiceName: voice.name,
          },
        });
      })
      .catch(function (error) {
        if (controller.signal.aborted) return; // user cancelled; state already updated
        dispatch({ type: "failed", error: toUserFacingError(error) });
      })
      .then(function () {
        if (abortController === controller) abortController = null;
      });
  }

  // ------------------------------------------------------------------ upload

  function handleFile(file) {
    if (!file || uploadChecking) return;
    var check = validateAudioFile(file);
    if (!check.ok) {
      dispatch({ type: "failed", error: { code: check.code, title: VALIDATION_TITLES[check.code], message: check.message } });
      return;
    }
    uploadChecking = true;
    render();
    getAudioDuration(file)
      .then(
        function (duration) {
          uploadChecking = false;
          var durationCheck = validateAudioDuration(duration);
          if (!durationCheck.ok) {
            dispatch({
              type: "failed",
              error: { code: durationCheck.code, title: VALIDATION_TITLES[durationCheck.code], message: durationCheck.message },
            });
            return;
          }
          acceptSource({
            blob: file,
            durationSeconds: duration,
            mimeType: file.type,
            fileName: file.name,
            origin: "upload",
          });
        },
        function () {
          uploadChecking = false;
          dispatch({
            type: "failed",
            error: {
              code: "unreadable-audio",
              title: "Couldn't read this file",
              message: "Your browser couldn't decode this audio. Try exporting it as MP3 or WAV and upload it again.",
            },
          });
        }
      );
  }

  // ------------------------------------------------------------------- views

  var dom = {};

  function viewRecorderIdle() {
    var requesting = rec.status === "requesting";
    return h(
      "div",
      { class: "dropzone" },
      h("div", { class: "icon-bubble" }, icon("mic", 28)),
      h(
        "div",
        { class: "stack-sm" },
        h("p", { class: "text-base semibold" }, "Record your voice"),
        h(
          "p",
          { class: "text-sm muted" },
          "Speak naturally — words, timing and emotion are preserved. Your browser will ask for microphone access."
        )
      ),
      button(
        {
          size: "lg",
          className: "btn-wide",
          key: "rec-start",
          disabled: requesting,
          icon: requesting ? icon("spinner", 18) : icon("mic", 18),
          onClick: recStart,
        },
        requesting ? "Waiting for microphone…" : "Record voice"
      ),
      h(
        "p",
        { class: "text-xs muted" },
        "Best results: " + RECOMMENDED_RANGE.min + "–" + RECOMMENDED_RANGE.max + " seconds • Maximum: " +
          limits.maxDurationSeconds + " seconds"
      )
    );
  }

  function viewRecorderActive() {
    var stopping = rec.status === "stopping";
    var canvas = h("canvas", { class: "level-meter", "aria-hidden": "true" });
    var panel = h(
      "div",
      { class: "recording-panel" },
      h(
        "div",
        { class: "row" },
        h(
          "div",
          { class: "rec-label" },
          h("span", { class: "rec-dot", "aria-hidden": "true" }),
          h("span", null, stopping ? "Finishing…" : "Recording")
        ),
        h(
          "p",
          { class: "timer tabular-nums", role: "timer", "aria-label": "Recording time" },
          h("span", { id: "rec-clock" }, formatClock(rec.elapsedMs / 1000)),
          " ",
          h("span", { class: "muted" }, "/ " + formatClock(limits.maxDurationSeconds))
        )
      ),
      canvas,
      h(
        "div",
        { class: "actions actions-center" },
        button(
          {
            variant: "danger",
            size: "lg",
            className: "btn-wide",
            key: "rec-stop",
            disabled: stopping,
            icon: stopping ? icon("spinner", 18) : icon("stop", 18),
            onClick: recStop,
          },
          stopping ? "Stopping…" : "Stop recording"
        ),
        button({ variant: "ghost", key: "rec-discard", disabled: stopping, onClick: recCancel }, "Discard")
      ),
      h("p", { id: "rec-hint", class: "text-xs muted center" }, "")
    );
    afterRender.push(function () {
      updateRecordingClock();
      startVisualizer(canvas);
    });
    return panel;
  }

  function viewUploadZone() {
    var input = h("input", {
      type: "file",
      id: "upload-input",
      class: "sr-only",
      accept: acceptAttribute(),
      tabindex: "-1",
      "aria-hidden": "true",
      disabled: uploadChecking,
      onChange: function (event) {
        var file = event.target.files && event.target.files[0];
        event.target.value = "";
        handleFile(file);
      },
    });
    var zone = h(
      "div",
      {
        class: "dropzone",
        onDragover: function (event) {
          event.preventDefault();
          zone.classList.add("is-dragging");
        },
        onDragleave: function () {
          zone.classList.remove("is-dragging");
        },
        onDrop: function (event) {
          event.preventDefault();
          zone.classList.remove("is-dragging");
          handleFile(event.dataTransfer && event.dataTransfer.files && event.dataTransfer.files[0]);
        },
      },
      h("div", { class: "icon-bubble" }, uploadChecking ? icon("spinner", 28) : icon("upload", 28)),
      h(
        "div",
        { class: "stack-sm" },
        h("p", { class: "text-base semibold" }, uploadChecking ? "Checking file…" : "Upload a recording"),
        h("p", { class: "text-sm muted" }, "Drag and drop an audio file here, or browse from your device.")
      ),
      input,
      button(
        {
          variant: "secondary",
          size: "lg",
          className: "btn-wide",
          key: "upload-choose",
          disabled: uploadChecking,
          describedBy: "upload-hint",
          icon: icon("upload", 18),
          onClick: function () {
            input.click();
          },
        },
        "Choose audio file"
      ),
      h(
        "p",
        { id: "upload-hint", class: "text-xs muted" },
        formatLabels().join(", ") + " • up to " + limits.maxDurationSeconds + " seconds • max " +
          formatBytes(limits.maxSizeBytes)
      )
    );
    return zone;
  }

  function viewSourcePreview(source, opts) {
    var isRecording = source.origin === "recording";
    var title = isRecording ? "Your recording" : source.fileName;
    return h(
      "div",
      { class: "box" },
      h(
        "div",
        { class: "row row-start" },
        h(
          "div",
          { class: "source-meta" },
          h("span", { class: "file-badge" }, icon("wave", 20)),
          h(
            "div",
            null,
            h("p", { class: "text-sm semibold truncate", title: title }, title),
            h(
              "p",
              { class: "text-xs muted" },
              (isRecording ? "Original" : "Original upload") + " • " + formatDurationHuman(source.durationSeconds) +
                " • " + formatBytes(source.blob.size)
            )
          )
        ),
        opts.compact
          ? null
          : button(
              {
                variant: "ghost",
                key: "discard",
                icon: isRecording ? icon("refresh", 16) : icon("trash", 16),
                onClick: discardSource,
              },
              isRecording ? "Re-record" : "Remove file"
            )
      ),
      h("audio", { class: "mt-3", controls: true, preload: "metadata", src: source.url, "aria-label": "Preview of " + title })
    );
  }

  function viewConsent() {
    return h(
      "label",
      { class: "consent" },
      h("input", {
        type: "checkbox",
        "data-key": "consent",
        checked: consentGiven,
        onChange: function (event) {
          consentGiven = event.target.checked;
          var btn = dom.panel.querySelector('[data-key="transform"]');
          if (btn) btn.disabled = !consentGiven;
        },
      }),
      h("span", null, "I confirm I have permission to use this recording.")
    );
  }

  function viewTransformRow(source) {
    var needsConsent = source.origin === "upload";
    var voice = selectedVoice();
    return h(
      "div",
      { class: "transform-row" },
      h(
        "p",
        { class: "text-sm muted" },
        "Target: ",
        h("span", { class: "medium", style: "color: var(--foreground)", id: "target-voice-name" }, voice.name)
      ),
      button(
        {
          size: "lg",
          key: "transform",
          disabled: needsConsent && !consentGiven,
          icon: icon("sparkles", 18),
          onClick: transform,
        },
        "Transform Voice"
      )
    );
  }

  function viewProcessing() {
    var voice = selectedVoice();
    var steps = h("ol", { class: "steps", id: "processing-steps" });
    var el = h(
      "div",
      { class: "box box-lg", role: "status", "aria-live": "polite", "aria-busy": "true" },
      h(
        "div",
        { class: "row" },
        h(
          "div",
          null,
          h("p", { class: "text-base semibold" }, "Transforming your performance…"),
          h(
            "p",
            { class: "text-sm muted" },
            "Rendering with " + voice.name + ". Longer recordings take a little longer."
          )
        ),
        h("p", { class: "text-sm muted tabular-nums", id: "processing-clock", "aria-hidden": "true" }, "0.0s")
      ),
      h("div", { class: "progress-track", "aria-hidden": "true" }, h("div", { class: "progress-bar" })),
      steps,
      h(
        "div",
        { class: "actions actions-end mt-4" },
        button({ variant: "ghost", key: "cancel", onClick: cancelProcessing }, "Cancel")
      )
    );
    afterRender.push(function () {
      updateProcessingSteps();
      var tick = function () {
        var clock = document.getElementById("processing-clock");
        if (clock && state.phase === "processing") {
          clock.textContent = Math.max(0, (performance.now() - state.startedAt) / 1000).toFixed(1) + "s";
        }
      };
      tick();
      processingTimer = window.setInterval(tick, 250);
    });
    return el;
  }

  function updateProcessingSteps() {
    var list = document.getElementById("processing-steps");
    if (!list || state.phase !== "processing") return;
    clear(list);
    var currentIndex = -1;
    STEPS.forEach(function (s, i) {
      if (s.id === state.step) currentIndex = i;
    });
    STEPS.forEach(function (item, index) {
      var done = index < currentIndex;
      var active = index === currentIndex;
      list.appendChild(
        h(
          "li",
          { class: "step" + (done ? " is-done" : active ? " is-active" : ""), "aria-current": active ? "step" : null },
          h(
            "span",
            { class: "step-dot", "aria-hidden": "true" },
            done ? icon("check", 12, 3) : active ? icon("spinner", 12) : null
          ),
          h(
            "span",
            null,
            item.label,
            h("span", { class: "sr-only" }, done ? " (done)" : active ? " (in progress)" : " (pending)")
          )
        )
      );
    });
  }

  function viewResult(result, source) {
    var seconds = (result.roundTripMs / 1000).toFixed(1);
    var blockedNote = h(
      "p",
      { class: "text-xs muted mt-2", hidden: true },
      "Autoplay was blocked by your browser — press play to listen."
    );
    var audio = h("audio", {
      class: "mt-4",
      controls: true,
      preload: "auto",
      src: result.url,
      "aria-label": "Transformed audio, " + result.voiceName,
    });

    afterRender.push(function () {
      // Browsers may refuse autoplay after an async request; the visible
      // controls remain the fallback.
      var attempt;
      try {
        attempt = audio.play();
      } catch (e) {
        attempt = Promise.reject(e);
      }
      if (attempt && typeof attempt.then === "function") {
        attempt.then(
          function () {
            blockedNote.hidden = true;
          },
          function () {
            if (audio.isConnected) blockedNote.hidden = false;
          }
        );
      }
    });

    return h(
      "div",
      { class: "stack" },
      h(
        "div",
        { class: "result-box", role: "status", "aria-live": "polite" },
        h(
          "div",
          { class: "row row-start" },
          h(
            "div",
            { class: "source-meta", style: "align-items: flex-start" },
            h("span", { class: "success-badge" }, icon("check", 16, 3)),
            h(
              "div",
              null,
              h(
                "p",
                { class: "text-base semibold", tabindex: "-1", "data-key": "result-heading" },
                "Your transformed voice is ready."
              ),
              h(
                "p",
                { class: "text-sm muted" },
                "Rendered as " + result.voiceName + " in " + seconds + "s • MP3 • " + formatBytes(result.blob.size)
              )
            )
          )
        ),
        audio,
        blockedNote,
        h(
          "div",
          { class: "actions mt-4" },
          h(
            "a",
            { class: "btn btn-primary", href: result.url, download: result.downloadName, "data-key": "download" },
            icon("download", 18),
            "Download MP3"
          ),
          button(
            { variant: "secondary", key: "reset", icon: icon("refresh", 18), onClick: resetAll },
            "Transform another recording"
          )
        )
      ),
      h(
        "details",
        { class: "box" },
        h("summary", null, "Compare with the original"),
        h(
          "div",
          { class: "compare-grid" },
          h(
            "div",
            null,
            h("p", { class: "text-xs muted medium" }, "Original"),
            h("audio", { controls: true, preload: "metadata", src: source.url, "aria-label": "Original audio" })
          ),
          h(
            "div",
            null,
            h("p", { class: "text-xs muted medium" }, "Transformed — " + result.voiceName),
            h("audio", {
              controls: true,
              preload: "metadata",
              src: result.url,
              "aria-label": "Transformed audio for comparison, " + result.voiceName,
            })
          )
        )
      )
    );
  }

  function viewErrorBanner(error, hasSource) {
    var actions = hasSource
      ? [
          button({ variant: "secondary", key: "error-action", onClick: transform }, "Try again"),
          button({ variant: "ghost", key: "error-reset", onClick: resetAll }, "Start over"),
        ]
      : [
          button(
            {
              variant: "ghost",
              key: "error-action",
              onClick: function () {
                pendingFocus = mode === "record" ? "rec-start" : "upload-choose";
                dispatch({ type: "retry" });
              },
            },
            "Dismiss"
          ),
        ];
    return h(
      "div",
      { class: "alert", role: "alert" },
      h("span", { class: "alert-icon" }, icon("alert", 20)),
      h(
        "div",
        { class: "alert-body" },
        h("p", { class: "text-sm semibold" }, error.title || "Something went wrong"),
        h("p", { class: "text-sm muted", style: "margin-top: 0.25rem" }, error.message),
        h("div", { class: "actions" }, actions)
      )
    );
  }

  // ------------------------------------------------------------------ render

  var afterRender = [];

  function statusMessage() {
    switch (state.phase) {
      case "recording":
        return "Recording started. It stops automatically at " + limits.maxDurationSeconds + " seconds.";
      case "source-ready":
        return state.source.origin === "recording" ? "Recording ready to transform." : "File ready to transform.";
      case "processing":
        return "Transforming your performance.";
      default:
        return "";
    }
  }

  function render() {
    if (!dom.panel) return;
    var active = document.activeElement;
    var focusKey = pendingFocus || (active && dom.panel.contains(active) ? active.getAttribute("data-key") : null);
    pendingFocus = null;

    // Detached <audio> elements keep playing; pause them before replacing.
    Array.prototype.forEach.call(dom.panel.querySelectorAll("audio"), function (a) {
      a.pause();
    });
    if (processingTimer !== null) {
      window.clearInterval(processingTimer);
      processingTimer = null;
    }
    stopVisualizer();
    afterRender = [];

    var phase = state.phase;
    var source = currentSource();
    var busy = phase === "recording" || phase === "processing" || rec.status !== "idle" || uploadChecking;
    var nodes = [];

    if (phase === "error") nodes.push(viewErrorBanner(state.error, !!source));
    if (phase === "result-ready") nodes.push(viewResult(state.result, source));
    if (phase === "processing") {
      nodes.push(viewSourcePreview(source, { compact: true }));
      nodes.push(viewProcessing());
    }
    if ((phase === "source-ready" || (phase === "error" && source)) && source) {
      nodes.push(viewSourcePreview(source, {}));
      if (source.origin === "upload") nodes.push(viewConsent());
      if (phase === "source-ready") nodes.push(viewTransformRow(source));
    }
    var noSource = phase === "idle" || phase === "recording" || (phase === "error" && !source);
    if (noSource && mode === "record") {
      nodes.push(rec.status === "recording" || rec.status === "stopping" ? viewRecorderActive() : viewRecorderIdle());
    }
    if ((phase === "idle" || (phase === "error" && !source)) && mode === "upload") nodes.push(viewUploadZone());

    clear(dom.panel);
    appendChildren(dom.panel, nodes);

    // Tabs and voice selector live outside the panel.
    var tabsDisabled = busy || !!source;
    dom.tabs.forEach(function (tab) {
      var selected = tab.getAttribute("data-mode") === mode;
      tab.setAttribute("aria-selected", selected ? "true" : "false");
      tab.tabIndex = selected ? 0 : -1;
      tab.disabled = tabsDisabled;
    });
    dom.panel.setAttribute("aria-labelledby", "source-tab-" + mode);
    dom.panel.id = "source-panel";
    if (dom.voiceFieldset) dom.voiceFieldset.disabled = phase === "processing";
    dom.status.textContent = statusMessage();

    afterRender.forEach(function (fn) {
      fn();
    });
    afterRender = [];

    if (focusKey) {
      var target = dom.panel.querySelector('[data-key="' + focusKey + '"]');
      if (target && !target.disabled) target.focus();
    }
  }

  // ------------------------------------------------------------------- mount

  function setMode(next, focus) {
    if (next === mode) return;
    mode = next;
    render();
    if (focus) {
      var tab = document.getElementById("source-tab-" + next);
      if (tab) tab.focus();
    }
  }

  function buildTabs() {
    var modes = [
      { id: "record", label: "Record", icon: "mic" },
      { id: "upload", label: "Upload", icon: "upload" },
    ];
    dom.tabs = modes.map(function (m) {
      return h(
        "button",
        {
          type: "button",
          role: "tab",
          class: "tab",
          id: "source-tab-" + m.id,
          "data-mode": m.id,
          "aria-controls": "source-panel",
          onClick: function () {
            setMode(m.id, false);
          },
          onKeydown: function (event) {
            var index = mode === "record" ? 0 : 1;
            var next = null;
            if (event.key === "ArrowRight" || event.key === "ArrowDown") next = (index + 1) % 2;
            if (event.key === "ArrowLeft" || event.key === "ArrowUp") next = (index + 1) % 2;
            if (event.key === "Home") next = 0;
            if (event.key === "End") next = 1;
            if (next === null) return;
            event.preventDefault();
            setMode(modes[next].id, true);
          },
        },
        icon(m.icon, 16),
        m.label
      );
    });
    return h("div", { role: "tablist", "aria-label": "Audio source", class: "tablist" }, dom.tabs);
  }

  function buildVoiceSelector() {
    dom.voiceGrid = h("div", { class: "voice-grid", role: "presentation" });
    dom.voiceFieldset = h(
      "fieldset",
      null,
      h(
        "legend",
        { class: "legend" },
        h("span", { class: "text-sm semibold" }, "Target voice"),
        h("span", { class: "text-xs muted" }, "Custom voices — coming later")
      ),
      dom.voiceGrid,
      h(
        "p",
        { class: "text-xs muted mt-2" },
        "Synthetic voices designed for this prototype. They are not modelled on real people."
      )
    );
    fillVoiceGrid();
    return dom.voiceFieldset;
  }

  function fillVoiceGrid() {
    var list = elevenVoices;
    var known = list.some(function (v) {
      return v.slug === voiceSlug;
    });
    if (!known && list.length) voiceSlug = list[0].slug;
    dom.voiceCards = list.map(function (voice) {
      var input = h("input", {
        type: "radio",
        name: "target-voice",
        value: voice.slug,
        class: "sr-only",
        checked: voice.slug === voiceSlug,
        onChange: function () {
          voiceSlug = voice.slug;
          syncVoiceCards();
          var label = document.getElementById("target-voice-name");
          if (label) label.textContent = selectedVoice().name;
        },
      });
      return h(
        "label",
        { class: "voice-card", "data-slug": voice.slug },
        input,
        h(
          "span",
          { class: "voice-card-head" },
          h("span", { class: "text-sm semibold" }, voice.name),
          h("span", { class: "check-dot", "aria-hidden": "true" })
        ),
        h("span", { class: "text-sm muted" }, voice.description || "")
      );
    });
    clear(dom.voiceGrid);
    appendChildren(dom.voiceGrid, dom.voiceCards);
    syncVoiceCards();
  }

  function syncVoiceCards() {
    dom.voiceCards.forEach(function (card) {
      var selected = card.getAttribute("data-slug") === voiceSlug;
      card.classList.toggle("is-selected", selected);
      var dot = card.querySelector(".check-dot");
      clear(dot);
      if (selected) dot.appendChild(icon("check", 12, 3));
    });
  }

  function statusDot(ok) {
    return h("span", { class: "status-dot" + (ok ? " is-ok" : ""), "aria-hidden": "true" });
  }

  /** Setup instructions shown in the blocking setup card. */
  function setupChecklist() {
    var voicesConfigured = elevenVoices.length > 0;
    return [
      h(
        "p",
        { class: "text-sm muted" },
        "Set the values below as environment variables (or in the task's ",
        h("code", { class: "inline-code" }, ".env"),
        " file) and restart ",
        h("code", { class: "inline-code" }, "python voice_transformer.py --serve"),
        "."
      ),
      h(
        "ul",
        { class: "checklist text-sm" },
        h(
          "li",
          null,
          statusDot(providerConfigured),
          h(
            "span",
            null,
            h("code", null, SETUP_API_KEY_VAR),
            " — a dedicated ElevenLabs API key" + (providerConfigured ? " (configured)" : " (missing)")
          )
        ),
        h(
          "li",
          null,
          statusDot(voicesConfigured),
          h(
            "span",
            null,
            "At least one target voice ID" + (voicesConfigured ? " (configured)" : " (none configured)") + ":",
            h(
              "ul",
              null,
              SETUP_VOICE_VARS.map(function (v) {
                return h("li", null, h("code", null, v.variable), " ", h("span", { class: "muted" }, "— " + v.name));
              })
            )
          )
        )
      ),
      h(
        "p",
        { class: "text-sm muted" },
        "Create the voices with ElevenLabs Voice Design (free plan), copy their voice IDs, and see the README for " +
          "the full step-by-step guide."
      ),
    ];
  }

  function mountTransformer(root) {
    voiceSlug = elevenVoices[0].slug;

    dom.status = h("p", { class: "sr-only", role: "status", "aria-live": "polite" });
    dom.panel = h("div", { role: "tabpanel", id: "source-panel", class: "stack" });

    var section = h(
      "section",
      { class: "card", "aria-labelledby": "transformer-heading" },
      h("h2", { id: "transformer-heading", class: "sr-only" }, "Voice transformer"),
      dom.status,
      h(
        "div",
        { class: "stack-lg" },
        buildVoiceSelector(),
        h(
          "div",
          { class: "stack" },
          h("div", { class: "row" }, h("p", { class: "text-sm semibold" }, "Source audio"), buildTabs()),
          dom.panel
        )
      )
    );
    clear(root);
    root.appendChild(section);
    render();
  }

  function mountSetupNotice(root) {
    clear(root);
    root.appendChild(
      h(
        "div",
        { class: "card setup-card" },
        h(
          "div",
          { class: "setup" },
          h("span", { class: "setup-icon" }, icon("info", 22)),
          h(
            "div",
            { class: "stack" },
            h(
              "div",
              null,
              h("h2", null, "Almost there — finish the ElevenLabs setup"),
              h(
                "p",
                { class: "text-sm muted mt-2" },
                "The app runs, but the server is missing the configuration needed to transform voices."
              )
            ),
            setupChecklist()
          )
        )
      )
    );
  }

  function mountLoadError(root) {
    clear(root);
    root.appendChild(
      h(
        "div",
        { class: "card" },
        h(
          "div",
          { class: "alert", role: "alert" },
          h("span", { class: "alert-icon" }, icon("alert", 20)),
          h(
            "div",
            { class: "alert-body" },
            h("p", { class: "text-sm semibold" }, "Couldn't load the app configuration"),
            h(
              "p",
              { class: "text-sm muted", style: "margin-top: 0.25rem" },
              "The server didn't respond as expected. Check that it is running, then reload the page."
            ),
            h(
              "div",
              { class: "actions" },
              button(
                {
                  variant: "secondary",
                  onClick: function () {
                    window.location.reload();
                  },
                },
                "Reload"
              )
            )
          )
        )
      )
    );
  }

  function hydrateStaticIcons() {
    Array.prototype.forEach.call(document.querySelectorAll("[data-icon]"), function (el) {
      el.appendChild(icon(el.getAttribute("data-icon"), Number(el.getAttribute("data-size")) || 20));
    });
  }

  function init() {
    hydrateStaticIcons();
    var root = document.getElementById("app-root");

    fetch(CONFIG_ENDPOINT, { cache: "no-store" })
      .then(function (response) {
        if (!response.ok) throw new Error("config " + response.status);
        return response.json();
      })
      .then(function (data) {
        config = data;
        config.formats = Array.isArray(config.formats) ? config.formats : [];
        elevenVoices = Array.isArray(config.voices) ? config.voices : [];
        var lim = config.limits || {};
        limits = {
          maxDurationSeconds: Number(lim.max_duration_s) || 30,
          maxSizeBytes: Math.round((Number(lim.max_size_mb) || 15) * 1024 * 1024),
        };
        Array.prototype.forEach.call(document.querySelectorAll("[data-max-duration]"), function (el) {
          el.textContent = String(limits.maxDurationSeconds);
        });

        providerConfigured =
          typeof config.provider_configured === "boolean" ? config.provider_configured : !!config.configured;
        elevenReady = !!config.configured && elevenVoices.length > 0;
        if (elevenReady) mountTransformer(root);
        else mountSetupNotice(root);
      })
      .catch(function () {
        mountLoadError(root);
      });

    // Release the microphone if the page is hidden mid-recording.
    window.addEventListener("pagehide", function () {
      if (rec.status !== "idle") recCancel();
      if (abortController) abortController.abort();
      objectUrls.slice().forEach(releaseUrl);
    });
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
