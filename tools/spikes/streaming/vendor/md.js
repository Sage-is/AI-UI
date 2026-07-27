// Spike-grade markdown subset. THROWAWAY — NOT a production renderer.
//
// Covers exactly what the spike's document exercises: headings, bold, italic,
// inline code, fenced code, unordered lists, paragraphs. It is here so the
// spike measures INCREMENTAL RENDERING BEHAVIOUR rather than a library choice.
//
// Production would not use this. The app already depends on marked, which in a
// no-build world ships as one content-hashed static file served immutable —
// the same asset story as the Svelte runtime. Nothing in this spike's finding
// depends on which renderer is used, only on whether partial documents can be
// re-rendered cheaply and without visual breakage.
//
// Escapes HTML first: the streamed text is untrusted in production, and a
// spike that models it as trusted would flatter itself.

const ESC = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' };
const escape = (s) => s.replace(/[&<>"]/g, (c) => ESC[c]);

export default function md(src) {
  const blocks = [];
  const lines = src.split('\n');
  let i = 0;

  while (i < lines.length) {
    const line = lines[i];

    if (line.startsWith('```')) {
      const lang = line.slice(3).trim();
      const body = [];
      i++;
      while (i < lines.length && !lines[i].startsWith('```')) body.push(lines[i++]);
      i++; // closing fence
      blocks.push(
        `<pre data-lang="${escape(lang)}"><code>${escape(body.join('\n'))}</code></pre>`
      );
      continue;
    }

    const heading = /^(#{1,6})\s+(.*)$/.exec(line);
    if (heading) {
      const level = heading[1].length;
      blocks.push(`<h${level}>${inline(heading[2])}</h${level}>`);
      i++;
      continue;
    }

    if (/^[-*]\s+/.test(line)) {
      const items = [];
      while (i < lines.length && /^[-*]\s+/.test(lines[i])) {
        items.push(`<li>${inline(lines[i].replace(/^[-*]\s+/, ''))}</li>`);
        i++;
      }
      blocks.push(`<ul>${items.join('')}</ul>`);
      continue;
    }

    if (line.trim() === '') { i++; continue; }

    const para = [];
    while (i < lines.length && lines[i].trim() !== ''
           && !lines[i].startsWith('```') && !/^[-*]\s+/.test(lines[i])
           && !/^#{1,6}\s/.test(lines[i])) {
      para.push(lines[i++]);
    }
    blocks.push(`<p>${inline(para.join(' '))}</p>`);
  }

  return blocks.join('');
}

function inline(text) {
  return escape(text)
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    .replace(/\*([^*]+)\*/g, '<em>$1</em>');
}
