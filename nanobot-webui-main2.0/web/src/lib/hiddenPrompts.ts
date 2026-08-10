export function normalizeHiddenPrompt(text: string): string {
  return text.replace(/\r\n/g, "\n").trim();
}

export interface HiddenPromptParseResult {
  prompts: string[];
  content: string;
}

export function extractHiddenPromptSegments(content: string, prompts: string[]): HiddenPromptParseResult {
  if (!content.trim() || prompts.length === 0) {
    return { prompts: [], content };
  }

  let remaining = content.replace(/\r\n/g, "\n").trim();
  const normalizedPrompts = prompts
    .map(normalizeHiddenPrompt)
    .filter(Boolean)
    .sort((a, b) => b.length - a.length);
  const matchedPrompts: string[] = [];

  let matched = true;
  while (matched && remaining) {
    matched = false;
    for (const prompt of normalizedPrompts) {
      if (remaining === prompt) {
        matchedPrompts.push(prompt);
        remaining = "";
        matched = true;
        break;
      }
      if (remaining.startsWith(`${prompt}\n\n`)) {
        matchedPrompts.push(prompt);
        remaining = remaining.slice(prompt.length + 2).trimStart();
        matched = true;
        break;
      }
    }
  }

  return { prompts: matchedPrompts, content: remaining };
}

export function stripHiddenPrompts(content: string, prompts: string[]): string {
  return extractHiddenPromptSegments(content, prompts).content;
}
