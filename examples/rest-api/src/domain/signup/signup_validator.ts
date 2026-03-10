// generated_from: behaviors/auth/signup
// spec_hash: 76de4dd5faf70d2285d59b7b3320eddbd2b2bb65e458c3cc5573b304b7c759d4
// generated_at: 2026-03-10T09:00:21.226835+00:00
// agent: implementation-agent
export class SignupValidator {
  static isValidEmail(email: string): boolean {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
  }

  static isPasswordStrong(password: string): boolean {
    const hasUppercase = /[A-Z]/;
    const hasDigit = /[0-9]/;
    const hasSpecial = /[!@#$%^&*(),.?":{}|<>]/;
    return (
      password.length >= 12 &&
      hasUppercase.test(password) &&
      hasDigit.test(password) &&
      hasSpecial.test(password)
    );
  }
}