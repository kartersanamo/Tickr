const DISCORD_CUSTOM_EMOJI = /^<a?:[a-zA-Z0-9_]{2,32}:\d{17,20}>$/;
const KEYCAP_EMOJI = /^[0-9#*]\uFE0F?\u20E3$/;
const ASCII_LETTERS = /[a-zA-Z]/;

const EMOJI_RANGES: [number, number][] = [
  [0x1f600, 0x1f64f],
  [0x1f300, 0x1f5ff],
  [0x1f680, 0x1f6ff],
  [0x1f900, 0x1f9ff],
  [0x1fa70, 0x1faff],
  [0x2600, 0x26ff],
  [0x2700, 0x27bf],
  [0x2300, 0x23ff],
  [0x2b50, 0x2b55],
  [0x1f1e6, 0x1f1ff],
];

const EMOJI_JOINERS = new Set([0x200d, 0xfe0f, 0x20e3]);

function codepointInEmojiRange(codepoint: number): boolean {
  if (EMOJI_JOINERS.has(codepoint)) {
    return true;
  }
  if (codepoint >= 0x1f3fb && codepoint <= 0x1f3ff) {
    return true;
  }
  for (const [start, end] of EMOJI_RANGES) {
    if (codepoint >= start && codepoint <= end) {
      return true;
    }
  }
  return false;
}

export function isValidTicketEmoji(value: string): boolean {
  const text = value.trim();
  if (!text || text.length > 128) {
    return false;
  }
  if (DISCORD_CUSTOM_EMOJI.test(text)) {
    return true;
  }
  if (KEYCAP_EMOJI.test(text)) {
    return true;
  }
  if (ASCII_LETTERS.test(text)) {
    return false;
  }

  let hasEmoji = false;
  for (let i = 0; i < text.length; ) {
    const codepoint = text.codePointAt(i) ?? 0;
    i += codepoint > 0xffff ? 2 : 1;

    if (codepointInEmojiRange(codepoint)) {
      if (!EMOJI_JOINERS.has(codepoint) && !(codepoint >= 0x1f3fb && codepoint <= 0x1f3ff)) {
        hasEmoji = true;
      }
      continue;
    }
    if ((codepoint >= 0x30 && codepoint <= 0x39) || codepoint === 0x23 || codepoint === 0x2a) {
      continue;
    }
    return false;
  }
  return hasEmoji;
}

export const TICKET_EMOJI_ERROR =
  "Enter a valid emoji (Unicode emoji or Discord custom emoji like <:name:123>). Plain text is not allowed.";
