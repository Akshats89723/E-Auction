/**
 * Password Visibility Toggle Helper
 * Automatically transforms password input fields into interactive show/hide inputs with Bootstrap eye icons.
 */
document.addEventListener('DOMContentLoaded', function () {
    function setupPasswordToggle(input, btn) {
        if (!input || !btn) return;
        btn.addEventListener('click', function (e) {
            e.preventDefault();
            const icon = btn.querySelector('i');
            if (input.type === 'password') {
                input.type = 'text';
                if (icon) {
                    icon.classList.remove('bi-eye', 'bi-eye-fill');
                    icon.classList.add('bi-eye-slash-fill');
                }
                btn.setAttribute('aria-label', 'Hide password');
                btn.title = "Hide Password";
            } else {
                input.type = 'password';
                if (icon) {
                    icon.classList.remove('bi-eye-slash', 'bi-eye-slash-fill');
                    icon.classList.add('bi-eye-fill');
                }
                btn.setAttribute('aria-label', 'Show password');
                btn.title = "Show Password";
            }
        });
    }

    // Bind custom toggle buttons
    document.querySelectorAll('.toggle-password-btn').forEach(function (btn) {
        const targetId = btn.getAttribute('data-target');
        let input = null;
        if (targetId) {
            input = document.getElementById(targetId);
        } else {
            const container = btn.closest('.modern-input-group') || btn.closest('.input-group') || btn.closest('.mb-3') || btn.parentElement;
            if (container) {
                input = container.querySelector('input');
            }
        }
        if (input) {
            input.dataset.hasPasswordToggle = "true";
            setupPasswordToggle(input, btn);
        }
    });

    // Auto-enhance remaining input[type="password"] fields
    document.querySelectorAll('input[type="password"]').forEach(function (input) {
        if (input.dataset.hasPasswordToggle) return;

        let parentGroup = input.closest('.modern-input-group') || input.closest('.input-group');
        let btn = parentGroup ? parentGroup.querySelector('.toggle-password-btn') : null;

        if (btn) {
            input.dataset.hasPasswordToggle = "true";
            setupPasswordToggle(input, btn);
            return;
        }

        if (!input.classList.contains('no-eye-toggle')) {
            input.dataset.hasPasswordToggle = "true";
            const wrapper = document.createElement('div');
            wrapper.className = 'input-group password-toggle-group';
            input.parentNode.insertBefore(wrapper, input);
            wrapper.appendChild(input);

            btn = document.createElement('button');
            btn.type = 'button';
            btn.className = 'btn btn-outline-secondary toggle-password-btn border-start-0 px-3';
            btn.setAttribute('aria-label', 'Show password');
            btn.title = "Show Password";
            btn.innerHTML = '<i class="bi bi-eye-fill"></i>';
            wrapper.appendChild(btn);

            setupPasswordToggle(input, btn);
        }
    });

});
