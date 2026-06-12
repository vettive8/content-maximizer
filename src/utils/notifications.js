/**
 * Notification Utility Module
 * Handles browser notifications and completion sounds.
 */

let notificationPermission = 'default';
let audioContext = null;
let unlockListenerAttached = false;

function getAudioContext() {
  const Ctx = window.AudioContext || window.webkitAudioContext;
  if (!Ctx) return null;
  if (!audioContext) {
    audioContext = new Ctx();
  }
  return audioContext;
}

function attachAudioUnlockListener() {
  if (unlockListenerAttached) return;
  unlockListenerAttached = true;

  const unlock = () => {
    const ctx = getAudioContext();
    if (ctx && ctx.state === 'suspended') {
      ctx.resume().catch(() => {});
    }
    document.removeEventListener('click', unlock);
    document.removeEventListener('keydown', unlock);
    unlockListenerAttached = false;
  };

  document.addEventListener('click', unlock, { once: true });
  document.addEventListener('keydown', unlock, { once: true });
}

export async function requestNotificationPermission() {
  if (!('Notification' in window)) {
    console.warn('This browser does not support notifications');
  }

  attachAudioUnlockListener();

  if (!('Notification' in window)) return false;
  if (Notification.permission === 'granted') {
    notificationPermission = 'granted';
    return true;
  }

  if (Notification.permission === 'denied') {
    notificationPermission = 'denied';
    return false;
  }

  const permission = await Notification.requestPermission();
  notificationPermission = permission;
  return permission === 'granted';
}

export async function playCompletionSound() {
  const ctx = getAudioContext();
  if (!ctx) return false;

  try {
    if (ctx.state === 'suspended') {
      await ctx.resume();
    }

    const sequence = [
      { freq: 659.25, time: 0.0, duration: 0.09 },
      { freq: 783.99, time: 0.1, duration: 0.09 },
      { freq: 987.77, time: 0.2, duration: 0.16 },
    ];

    const now = ctx.currentTime + 0.01;
    sequence.forEach((note) => {
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = 'triangle';
      osc.frequency.setValueAtTime(note.freq, now + note.time);
      gain.gain.setValueAtTime(0.0001, now + note.time);
      gain.gain.exponentialRampToValueAtTime(0.18, now + note.time + 0.02);
      gain.gain.exponentialRampToValueAtTime(0.0001, now + note.time + note.duration);
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start(now + note.time);
      osc.stop(now + note.time + note.duration + 0.02);
    });
    return true;
  } catch (error) {
    console.warn('Completion sound failed:', error);
    return false;
  }
}

export function showNotification(title, options = {}) {
  const {
    body = '',
    icon,
    focusWindow = false,
    tag = 'agent-complete',
    playSound = false,
  } = options;

  if (playSound) {
    playCompletionSound();
  }

  if (focusWindow && document.hidden) {
    window.focus();
  }

  if (!('Notification' in window)) {
    return null;
  }

  if (!(notificationPermission === 'granted' || Notification.permission === 'granted')) {
    return null;
  }

  const notification = new Notification(title, {
    body,
    icon,
    badge: icon,
    tag,
    requireInteraction: false,
    silent: false,
  });

  notification.onclick = () => {
    window.focus();
    notification.close();
  };

  setTimeout(() => notification.close(), 5000);
  return notification;
}

export function notifyContentMaximizerComplete(projectTitle) {
  return showNotification('Content Maximizer Complete', {
    body: `"${projectTitle}" is ready. Clips, blog, and social posts were generated.`,
    tag: 'cm-complete',
    playSound: true,
  });
}

export function notifyBusinessGrowthStrategyComplete(businessModel) {
  return showNotification('Business Growth Strategy Ready', {
    body: `Your ${businessModel} strategy is complete and ready to review.`,
    tag: 'bgs-complete',
    playSound: true,
  });
}

// Backward-compatible alias for existing imports.
export const notifyGamePlanComplete = notifyBusinessGrowthStrategyComplete;

requestNotificationPermission();

