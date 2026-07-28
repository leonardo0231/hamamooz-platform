import test from 'node:test';
import assert from 'node:assert/strict';
import { flattenFieldErrors, humanizeApiError, networkError } from '../dist/assets/api/errors.js';

test('validation details are mapped to field errors', () => {
  assert.deepEqual(flattenFieldErrors({ username: ['required'], password: 'invalid' }), {
    username: ['required'],
    password: ['invalid'],
  });
});

test('wrapped API errors preserve code, request id and message', () => {
  const error = humanizeApiError(400, {
    error: {
      code: 'validation_error',
      detail: { username: ['نام کاربری الزامی است.'] },
      request_id: 'request-123',
    },
  });
  assert.equal(error.code, 'validation_error');
  assert.equal(error.requestId, 'request-123');
  assert.equal(error.message, 'نام کاربری الزامی است.');
});

test('network failures receive a safe end-user message', () => {
  const error = networkError(new Error('socket closed'));
  assert.equal(error.status, 0);
  assert.equal(error.code, 'network_error');
  assert.match(error.message, /ارتباط با سرور/);
});
