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
    model: 'test'
  }));

  submitQuery('Show reports');

  await waitFor(() => expect(document.getElementById('queryOutput').textContent).toBe(sql));
  const output = document.getElementById('queryOutput');
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
