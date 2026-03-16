(function (global) {
  'use strict';

  function cpToDigits(cp) {
    if (cp === 0) return [0];
    const out = [];
    let n = cp;
    while (n > 0) {
      const d = n % 60;
      out.push(d);
      n = Math.floor(n / 60);
    }
    return out.reverse();
  }

  function encodeToControlStream(message) {
    const digits = [];
    for (const ch of message) {
      const cp = ch.codePointAt(0);
      const ds = cpToDigits(cp);
      for (const d of ds) digits.push(d);
      digits.push(0x1c); // FS separator
    }
    if (digits.length && digits[digits.length - 1] === 0x1c) digits.pop();
    return digits;
  }

  function signFor(code) {
    if (code === 0x07) return 0;
    if ((code >= 0x00 && code <= 0x06) || (code >= 0x1c && code <= 0x3b)) return 1;
    if (code >= 0x08 && code <= 0x1b) return -1;
    throw new Error('SIGN_VALUE_DECODE_ERROR');
  }

  function canonicalizeDigits(digits) {
    const ORBIT_BASE = 36;
    const frameTotals = [0];
    const belCounts = [0];
    const frameValues = [];

    for (const code of digits) {
      if (code < 0 || code > 0x3b) throw new Error('INVALID_CONTROL_CODE_RANGE');
      if (code >= 0x3c && code <= 0x3f) throw new Error('RESERVED_CONTROL_CODE');

      if (code === 0x1c && frameTotals[frameTotals.length - 1] !== 0) {
        frameValues.push(((frameTotals[frameTotals.length - 1] % ORBIT_BASE) + ORBIT_BASE) % ORBIT_BASE);
        frameTotals.push(0);
        belCounts.push(0);
      }

      if (code === 0x00) continue; // NUL identity
      if (code === 0x07) {
        const sign = (belCounts[belCounts.length - 1] % 2 === 0) ? 1 : -1;
        frameTotals[frameTotals.length - 1] += sign * 0x07;
        belCounts[belCounts.length - 1] += 1;
      } else {
        frameTotals[frameTotals.length - 1] += signFor(code) * code;
      }
    }

    frameValues.push(((frameTotals[frameTotals.length - 1] % ORBIT_BASE) + ORBIT_BASE) % ORBIT_BASE);

    let patternNumber = 0;
    for (let i = 0; i < frameValues.length; i++) {
      patternNumber += frameValues[i] * (ORBIT_BASE ** i);
    }
    return { frameValues, patternNumber };
  }

  async function sha256Tagged(text) {
    const enc = new TextEncoder().encode(text);
    const hash = await crypto.subtle.digest('SHA-256', enc);
    const hex = Array.from(new Uint8Array(hash)).map(b => b.toString(16).padStart(2, '0')).join('');
    return 'sha256:' + hex;
  }

  async function buildMessageArtifact(message, tick) {
    const digits = encodeToControlStream(message);
    const c = canonicalizeDigits(digits);
    const base = {
      message,
      control_digits: digits,
      canonicalization: 'stream-sign-value-v1',
      orbit_base: 36,
      frame_values: c.frameValues,
      pattern_number: c.patternNumber,
      tick: tick || 8,
      note: 'Serverless browser artifact. Hash uses WebCrypto sha256.'
    };
    const canonical = JSON.stringify(base);
    const digest = await sha256Tagged(canonical);
    base.stream_digest = digest;
    return base;
  }

  global.AtomicKernel = {
    encodeToControlStream,
    canonicalizeDigits,
    sha256Tagged,
    buildMessageArtifact
  };
})(window);
