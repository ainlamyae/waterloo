/**
 * Minimal Markdown -> HTML renderer for a specific subset:
 * `##`/`###`/`####` headings with optional
 * `{#id}` anchors, paragraphs, bold/italic emphasis, [text](url) links,
 * `-`/`1.` lists (2-space nesting), and GFM-style pipe tables.
 *
 * Content is generated locally from a trusted source document (not
 * user input), so this intentionally does not HTML-escape text --
 * that also lets table cells carry the literal `<br>` our converter
 * inserts between paragraphs within a single cell.
 */
(function (global) {
  function inline(text) {
    return text
      .replace(
        /\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g,
        '<a dir="ltr" href="$2" target="_blank" rel="noopener noreferrer">$1</a>'
      )
      // auto-linkify bare URLs left over from table cells / plain text (skip
      // ones already turned into a link above, recognizable by the quote or
      // `>` immediately preceding them)
      .replace(/(^|[^"'>])(https?:\/\/[^\s<]+)/g, (m, pre, url) => {
        return `${pre}<a dir="ltr" href="${url}" target="_blank" rel="noopener noreferrer">${url}</a>`;
      })
      // format bare 10-digit Canadian/US phone numbers as (XXX) XXX-XXXX
      // and make them tap-to-dial
      .replace(/(^|[^"'>\d])(\d{10})(?!\d)/g, (m, pre, digits) => {
        const formatted = `(${digits.slice(0, 3)}) ${digits.slice(3, 6)}-${digits.slice(6)}`;
        return `${pre}<a dir="ltr" href="tel:+1${digits}">${formatted}</a>`;
      })
      .replace(/\*\*([^*]+?)\*\*/g, "<strong>$1</strong>")
      .replace(/\*([^*]+?)\*/g, "<em>$1</em>");
  }

  function renderParagraph(text) {
    return "<p>" + text.split("\n").map(inline).join("<br>") + "</p>";
  }

  function renderHeading(block) {
    const m = block.match(/^(#{2,4})\s+(.*)$/);
    const hashes = m[1];
    let rest = m[2].trim();
    let id = "";
    const idMatch = rest.match(/^(.*?)\s*\{#([\w-]+)\}\s*$/);
    if (idMatch) {
      rest = idMatch[1];
      id = idMatch[2];
    }
    const level = hashes.length;
    const idAttr = id ? ` id="${id}"` : "";
    return `<h${level}${idAttr}>${inline(rest)}</h${level}>`;
  }

  function renderList(block) {
    const lines = block.split("\n").filter((l) => l.trim());
    let i = 0;
    function parse(level) {
      const items = [];
      while (i < lines.length) {
        const line = lines[i];
        const m = line.match(/^(\s*)(-|\d+\.)\s+(.*)$/);
        if (!m) break;
        const curLevel = Math.floor(m[1].length / 2);
        if (curLevel < level) break;
        if (curLevel > level) {
          items[items.length - 1].sub += parse(curLevel);
          continue;
        }
        const ordered = /^\d+\.$/.test(m[2]);
        i++;
        items.push({ text: inline(m[3]), ordered, sub: "" });
      }
      if (!items.length) return "";
      const tag = items[0].ordered ? "ol" : "ul";
      const inner = items.map((it) => `<li>${it.text}${it.sub}</li>`).join("");
      return `<${tag}>${inner}</${tag}>`;
    }
    return parse(0);
  }

  function renderTable(block) {
    const lines = block.split("\n").filter((l) => l.trim());
    const parseRow = (line) =>
      line.trim().replace(/^\|/, "").replace(/\|$/, "").split("|").map((c) => c.trim());
    const header = parseRow(lines[0]);
    const bodyLines = lines.slice(2);
    let html = '<div class="table-wrap"><table><thead><tr>';
    header.forEach((h) => (html += `<th>${inline(h)}</th>`));
    html += "</tr></thead><tbody>";
    bodyLines.forEach((line) => {
      const cells = parseRow(line);
      html += "<tr>" + cells.map((c) => `<td>${inline(c)}</td>`).join("") + "</tr>";
    });
    html += "</tbody></table></div>";
    return html;
  }

  function render(markdown) {
    const blocks = markdown.trim().split(/\n{2,}/);
    return blocks
      .map((block) => {
        const trimmed = block.trim();
        if (!trimmed) return "";
        // raw HTML block (e.g. a hand-authored video/map embed): pass through
        // untouched instead of wrapping in <p>, since it's not inline text
        if (/^</.test(trimmed)) return trimmed;
        if (/^#{2,4}\s+/.test(trimmed)) return renderHeading(trimmed);
        if (trimmed.split("\n").every((l) => /^\s*\|/.test(l))) return renderTable(trimmed);
        if (trimmed.split("\n").every((l) => /^\s*(-|\d+\.)\s+/.test(l))) return renderList(trimmed);
        return renderParagraph(trimmed);
      })
      .join("\n");
  }

  global.MiniMarkdown = { render };
})(window);
