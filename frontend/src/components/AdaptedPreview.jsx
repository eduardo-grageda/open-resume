import ReactMarkdown from 'react-markdown';

export default function AdaptedPreview({ markdown, jobTitle = 'CV', companyName = '' }) {
  const handlePrint = () => {
    const w = window.open('', '_blank');
    const title = companyName ? `${jobTitle} at ${companyName}` : (jobTitle || 'CV');
    const html = `<!DOCTYPE html><html><head><meta charset="UTF-8"><title>${title}</title>
<style>
  @page { size: A4; margin: 2cm; }
  body {
    font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;
    font-size: 11pt;
    line-height: 1.6;
    color: #1a1a1a;
    max-width: 700px;
    margin: 0 auto;
    padding: 2rem;
  }
  h1 { font-size: 18pt; margin-bottom: 4pt; }
  h2 { font-size: 14pt; border-bottom: 1px solid #ddd; padding-bottom: 4pt; margin-top: 16pt; }
  h3 { font-size: 12pt; }
  ul, ol { padding-left: 1.2em; }
  li { margin-bottom: 2pt; }
  hr { border: none; border-top: 1px solid #ddd; margin: 16pt 0; }
  p { margin-bottom: 4pt; }
  .change-summary {
    margin-top: 24pt;
    padding: 12pt;
    background: #f8f9fa;
    border-left: 3pt solid #2563eb;
    font-size: 10pt;
  }
</style></head>
<body><div id="content"></div></body></html>`;
    w.document.write(html);
    w.document.close();
    w.document.getElementById('content').innerHTML = markdownToHtml(markdown);
    setTimeout(() => w.print(), 500);
  };

  return (
    <div>
      <div className="inline-row gap-1 mb-2">
        <button className="btn btn-primary btn-sm" onClick={handlePrint}>
          Print Preview
        </button>
      </div>
      <div className="adapted-preview">
        <ReactMarkdown>{markdown}</ReactMarkdown>
      </div>
    </div>
  );
}

function markdownToHtml(md) {
  let html = md;

  html = html.replace(/^### (.+)$/gm, '<h3>$1</h3>');
  html = html.replace(/^## (.+)$/gm, '<h2>$1</h2>');
  html = html.replace(/^# (.+)$/gm, '<h1>$1</h1>');

  html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
  html = html.replace(/\*(.+?)\*/g, '<em>$1</em>');

  html = html.replace(/^- (.+)$/gm, '<li>$1</li>');
  html = html.replace(/(<li>.*<\/li>\n?)+/g, '<ul>$&</ul>');

  html = html.replace(/^---$/gm, '<hr>');

  html = html.split(/\n{2,}/).map(block => {
    if (block.match(/^<[hul]/)) return block;
    return `<p>${block.replace(/\n/g, '<br>')}</p>`;
  }).join('\n');

  return html;
}