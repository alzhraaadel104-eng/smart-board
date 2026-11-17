"""Generate a small, safe interaction starter for a sketch-generated page."""

from app.layout.layout_engine import prepare_elements


def generate_javascript(data):
    """Return progressive-enhancement behavior for generated buttons and fields."""
    prepare_elements(data)
    return """(() => {
  const canvas = document.querySelector('.sketch-canvas');
  if (!canvas) return;

  const status = document.createElement('p');
  status.className = 'interaction-status';
  status.setAttribute('role', 'status');
  status.setAttribute('aria-live', 'polite');
  status.hidden = true;
  canvas.append(status);

  const showStatus = (message) => {
    status.textContent = message;
    status.hidden = false;
  };

  canvas.querySelectorAll('.sketch-button').forEach((button) => {
    button.addEventListener('click', () => {
      const emptyField = [...canvas.querySelectorAll('.sketch-input')]
        .find((field) => !field.value.trim());

      if (emptyField) {
        emptyField.setAttribute('aria-invalid', 'true');
        emptyField.focus();
        showStatus('Please complete the fields before continuing.');
        return;
      }

      showStatus(`${button.textContent.trim() || 'Button'} clicked. Connect this action to your application.`);
    });
  });

  canvas.querySelectorAll('.sketch-input').forEach((field) => {
    field.addEventListener('input', () => field.removeAttribute('aria-invalid'));
  });
})();
"""
