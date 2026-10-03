// Password rules for signup and password changes. The backend enforces the
// same ones (validate_new_password in backend/app/api/routes/auth.py).
export const MIN_PASSWORD_LENGTH = 8;
export const MAX_PASSWORD_BYTES = 72;

export const passwordChecks = (password) => ({
  hasMinLength: password.length >= MIN_PASSWORD_LENGTH,
  hasUpper: /[A-Z]/.test(password),
  // Any character that isn't a letter or digit counts as a symbol (incl. - and _).
  hasSymbol: /[^A-Za-z0-9]/.test(password),
  fitsBcrypt: new TextEncoder().encode(password).length <= MAX_PASSWORD_BYTES,
});

// The first rule a password breaks, as a sentence, or null if it is fine.
export const passwordProblem = (password) => {
  const checks = passwordChecks(password);
  if (!checks.hasMinLength) return `Password must be at least ${MIN_PASSWORD_LENGTH} characters.`;
  if (!checks.fitsBcrypt) return `Password must be at most ${MAX_PASSWORD_BYTES} bytes.`;
  if (!checks.hasUpper) return 'Password must contain an uppercase letter.';
  if (!checks.hasSymbol) return 'Password must contain a symbol.';
  return null;
};
