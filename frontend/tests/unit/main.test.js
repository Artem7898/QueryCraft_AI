import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { waitFor } from '@testing-library/dom';
import fetchMock from 'jest-fetch-mock';

const html = readFileSync(join(__dirname, '../../public/index.html'), 'utf8');
const body = new DOMParser().parseFromString(html, 'text/html').body.innerHTML;
const generateUrl = 'http://localhost:8000/api/v1/generate';

function submitQuery(text) {
  document.getElementById('queryInput').value = text;
  document.getElementById('queryForm').dispatchEvent(new Event('submit', { cancelable: true }));
}

beforeEach(() => {
  jest.useFakeTimers();
  jest.resetModules();
  document.body.innerHTML = body;
  document.getElementById('result').scrollIntoView = jest.fn();
  fetchMock.mockResponseOnce(JSON.stringify({ status: 'healthy' }));
  require('../../public/assets/js/i18n.js');
  require('../../public/assets/js/main.js');
  document.dispatchEvent(new Event('DOMContentLoaded'));
});

afterEach(() => {
  jest.useRealTimers();
});

test('opens and closes the query modal', () => {
  const modal = document.getElementById('queryModal');
  expect(modal).toHaveClass('hidden');
  document.getElementById('openModal').click();
  expect(modal).not.toHaveClass('hidden');
  document.getElementById('closeModal').click();
  jest.advanceTimersByTime(300);
  expect(modal).toHaveClass('hidden');
});

test('keeps the modal open during input and closes it with Escape', () => {
  const modal = document.getElementById('queryModal');
  const input = document.getElementById('queryInput');
  document.getElementById('openModal').click();
  input.click();
  input.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', bubbles: true }));
  expect(modal).not.toHaveClass('hidden');

  input.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }));
  jest.advanceTimersByTime(300);
  expect(modal).toHaveClass('hidden');
});

test('updates the character count and switches the language', () => {
  const input = document.getElementById('queryInput');
  input.value = 'Show active users';
  input.dispatchEvent(new Event('input'));
  expect(document.getElementById('charCount')).toHaveTextContent('17');

  document.getElementById('langBtn').click();
  expect(document.documentElement.lang).toBe('en');
  expect(document.getElementById('currentLang')).toHaveTextContent('EN');
});

test('asks for a non-empty description without sending it', () => {
  document.getElementById('langBtn').click();
  submitQuery(' \t ');
  expect(document.body).toHaveTextContent('Please describe your query');
  expect(fetchMock).toHaveBeenCalledTimes(1);
});

test('submits the description and displays generated SQL as exact highlighted text', async () => {
  const sql = "select '<note>draft</note>' from reports where total > 12 -- sample\n";
  fetchMock.mockResponseOnce(JSON.stringify({
    query: sql,
    explanation: 'Example query',
    executed_in: 0.1,
    model: 'test',
    source: 'live'
  }));

  document.getElementById('schemaContext').value = ' \n\t ';
  submitQuery('Show reports');

  await waitFor(() => expect(document.getElementById('queryOutput').textContent).toBe(sql));
  const output = document.getElementById('queryOutput');
  const source = document.getElementById('liveResultSource');
  expect(source).not.toHaveClass('hidden');
  expect(source).toHaveTextContent('Сгенерировано моделью');
  expect(document.getElementById('demoResultSource')).toHaveClass('hidden');
  expect(document.getElementById('executionTime').textContent).toBe('Время: 0.1 сек. | Модель: test');
  expect(output.querySelector('note')).toBeNull();
  expect(output.querySelector('.font-semibold')).toHaveTextContent('select');
  expect(output.querySelector('.text-blue-600')).toHaveTextContent('12');
  expect(output.querySelector('.italic')).toHaveTextContent('-- sample');
  expect(fetchMock).toHaveBeenCalledWith(generateUrl, expect.objectContaining({
    method: 'POST',
    body: JSON.stringify({
      text: 'Show reports',
      db_type: 'postgresql',
      complexity: 'simple',
      language: 'ru'
    })
  }));
  document.getElementById('copyBtn').click();
  expect(navigator.clipboard.writeText).toHaveBeenCalledWith(sql);
  await waitFor(() => expect(document.getElementById('copyBtn')).toHaveTextContent('Скопировано'));
});

test('sends the schema context, selected options and genuine description', async () => {
  const input = document.getElementById('schemaContext');
  const schema = 'accounts(account_id, name)\ninvoices(account_id, due_at, paid_at)';
  document.getElementById('langBtn').click();
  expect(input).toHaveAccessibleName('Database schema (optional)');
  expect(input).toHaveAccessibleDescription(/tables or collections/);
  expect(input).toHaveAttribute('maxlength', '3000');
  input.value = '  ' + schema + '\n ';
  document.getElementById('dbType').value = 'sqlite';
  document.getElementById('complexity').value = 'advanced';
  fetchMock.mockResponseOnce(JSON.stringify({
    query: 'SELECT name FROM accounts;',
    explanation: 'Query for the selected schema',
    executed_in: 0.1,
    model: 'test',
    source: 'live'
  }));

  const description = 'List accounts with overdue invoices';
  submitQuery(description);

  const source = document.getElementById('liveResultSource');
  await waitFor(() => expect(source).not.toHaveClass('hidden'));
  expect(source).toHaveTextContent('Generated by a model');
  const [, request] = fetchMock.mock.calls.find(([url]) => url === generateUrl);
  expect(JSON.parse(request.body)).toEqual({
    text: description,
    db_type: 'sqlite',
    complexity: 'advanced',
    language: 'en',
    schema_context: schema
  });
});

test.each([
  ['bytez', ' (Bytez)'],
  ['openai', ' (OpenAI)'],
  ['ollama', ' (Ollama)'],
  ['unknown', '']
])('displays live generation metadata for the %s provider', async (provider, label) => {
  document.getElementById('langBtn').click();
  fetchMock.mockResponseOnce(JSON.stringify({
    query: 'SELECT name FROM accounts;',
    explanation: 'Query for the selected schema',
    executed_in: 0.1,
    model: 'test',
    source: 'live',
    provider
  }));

  submitQuery('List accounts');

  const metadata = document.getElementById('executionTime');
  await waitFor(() => expect(metadata.textContent).toBe(`Time: 0.1 sec. | Model: test${label}`));
});

test('rejects a schema value longer than the input limit before sending', () => {
  const input = document.getElementById('schemaContext');
  input.value = 'x'.repeat(input.maxLength + 1);
  submitQuery('Show reports');

  expect(document.body).toHaveTextContent('Описание схемы должно содержать не более 3000 символов');
  expect(fetchMock).toHaveBeenCalledTimes(1);
});

test('identifies a demo template in both languages without calling it model-generated', async () => {
  fetchMock.mockResponseOnce(JSON.stringify({
    query: 'SELECT * FROM example_table;',
    explanation: 'Fixed example',
    executed_in: 0,
    model: 'test',
    source: 'demo',
    provider: null
  }));
  submitQuery('Show reports');

  const source = document.getElementById('demoResultSource');
  await waitFor(() => expect(source).not.toHaveClass('hidden'));
  expect(source).toHaveTextContent('Демонстрационный шаблон');
  expect(document.getElementById('liveResultSource')).toHaveClass('hidden');
  expect(document.getElementById('executionTime').textContent).toBe('Время: 0 сек. | Модель: test');
  document.getElementById('langBtn').click();
  expect(source).toHaveTextContent('Demo template');
  expect(document.getElementById('liveResultSource')).toHaveClass('hidden');
});

test('handles 503 with localized setup guidance and hides prior results', async () => {
  fetchMock.mockResponseOnce(JSON.stringify({
    query: 'SELECT * FROM example_table;',
    explanation: 'Fixed example',
    executed_in: 0,
    model: 'test',
    source: 'demo'
  }));
  submitQuery('Show reports');
  await waitFor(() => expect(document.getElementById('result')).not.toHaveClass('hidden'));

  fetchMock.mockResponseOnce(JSON.stringify({ detail: 'Internal routing details' }), { status: 503 });
  submitQuery('Show another report');

  const alert = document.getElementById('generationUnavailable');
  await waitFor(() => expect(alert).not.toHaveClass('hidden'));
  expect(alert).toHaveTextContent('Настройте провайдера на сервере');
  expect(alert).toHaveTextContent('Для локальной генерации можно использовать Ollama.');
  expect(document.getElementById('result')).toHaveClass('hidden');
  expect(document.body).not.toHaveTextContent('Internal routing details');
  expect(document.querySelector('#queryForm button[type="submit"]')).toBeEnabled();
  document.getElementById('langBtn').click();
  expect(alert).toHaveTextContent('Configure a provider on the server');
  expect(alert).toHaveTextContent('Ollama can run generation locally.');
});

test('shows a network error and re-enables submission', async () => {
  document.getElementById('langBtn').click();
  fetchMock.mockRejectOnce(new Error('Connection unavailable'));
  submitQuery('Show reports');
  await waitFor(() => expect(document.getElementById('queryOutput')).toHaveTextContent('Connection unavailable'));
  expect(document.getElementById('explanation')).toHaveTextContent('Check backend connection.');
  expect(document.querySelector('#queryForm button[type="submit"]')).toBeEnabled();
});

test('uses the HTTP status when the server returns structured validation details', async () => {
  fetchMock.mockResponseOnce(JSON.stringify({
    detail: [{ msg: 'Invalid value', loc: ['body', 'text'] }]
  }), { status: 422 });
  submitQuery('Show reports');
  await waitFor(() => expect(document.getElementById('queryOutput')).toHaveTextContent('HTTP error 422'));
});
