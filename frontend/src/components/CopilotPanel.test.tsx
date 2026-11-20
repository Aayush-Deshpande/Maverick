import { describe, expect, it } from 'vitest';
import { renderToStaticMarkup } from 'react-dom/server';
import CopilotPanel from './CopilotPanel';

const api = async () => ({});

describe('CopilotPanel', () => {
  it('offers the one-click operator questions and a free-text box', () => {
    const html = renderToStaticMarkup(<CopilotPanel engineId="e" api={api} />);
    for (const q of ['What is going on?', 'What should I do right now?', 'How do I fix it?']) expect(html).toContain(q);
    expect(html).toContain('Or type your own question');
  });
  it('cannot ask before an engine is selected', () => {
    const html = renderToStaticMarkup(<CopilotPanel engineId={null} api={api} />);
    expect((html.match(/disabled=""/g) ?? []).length).toBeGreaterThanOrEqual(5);
  });
});
