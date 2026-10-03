document.addEventListener("DOMContentLoaded", () => {

    // Show a spinner + disable the button while a form's request is in flight.
    // Loading text/behavior lives on the clicked BUTTON (via event.submitter),
    // since one form can have multiple submit buttons with different actions
    // (e.g. the inventory page's "Generate Recipe" vs "Remove Selected").
    document.querySelectorAll("form[data-animated]").forEach((form) => {
        form.addEventListener("submit", (event) => {
            const button = event.submitter || form.querySelector("button[type=submit]");

            if (!button) {
                return;
            }

            const requireChecked = button.dataset.requireChecked;

            if (requireChecked) {
                const checked = form.querySelectorAll(
                    `input[name="${requireChecked}"]:checked`
                );

                if (checked.length === 0) {
                    event.preventDefault();
                    alert(button.dataset.emptyMessage || "Select at least one item first.");
                    return;
                }
            }

            if (form.dataset.submitting === "true") {
                event.preventDefault();
                return;
            }

            form.dataset.submitting = "true";
            button.disabled = true;
            button.dataset.originalText = button.textContent;
            button.innerHTML = `<span class="spinner"></span>${button.dataset.loadingText || "Working..."}`;
        });
    });

    // Reflect the chosen filename in the dropzone label instead of the default placeholder.
    document.querySelectorAll(".dropzone input[type=file]").forEach((input) => {
        const label = input.closest(".dropzone").querySelector("span");
        const defaultText = label.textContent;

        input.addEventListener("change", () => {
            if (input.files && input.files.length > 0) {
                label.textContent = `✓ ${input.files[0].name}`;
                input.closest(".dropzone").classList.add("has-file");
            } else {
                label.textContent = defaultText;
                input.closest(".dropzone").classList.remove("has-file");
            }
        });
    });

    // Grocery statement textarea: auto-grow to fit content, and let the
    // example chips fill it in with a little pulse so it's obvious
    // something happened.
    const statementInput = document.getElementById("statement-input");

    if (statementInput) {
        const autoGrow = () => {
            statementInput.style.height = "auto";
            statementInput.style.height = `${statementInput.scrollHeight}px`;
        };

        statementInput.addEventListener("input", autoGrow);
        autoGrow();

        document.querySelectorAll(".chip").forEach((chip) => {
            chip.addEventListener("click", () => {
                statementInput.value = chip.dataset.fill || "";
                autoGrow();
                statementInput.focus();
                statementInput.classList.remove("pulse");
                // Re-trigger the animation even if it just played.
                void statementInput.offsetWidth;
                statementInput.classList.add("pulse");
            });
        });
    }

    // Subtle parallax: the background gently drifts toward the pointer,
    // on top of its own ambient animation. Skipped if the OS asks for
    // reduced motion, or on devices with no real pointer (most touch-only
    // phones), where it would add nothing but battery drain.
    const bgFx = document.querySelector(".bg-fx");
    const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const hasFinePointer = window.matchMedia("(pointer: fine)").matches;

    if (bgFx && !prefersReducedMotion && hasFinePointer) {
        let targetX = 0;
        let targetY = 0;
        let currentX = 0;
        let currentY = 0;

        window.addEventListener("pointermove", (event) => {
            targetX = (event.clientX / window.innerWidth) - 0.5;
            targetY = (event.clientY / window.innerHeight) - 0.5;
        });

        const AMPLITUDE = 22; // max drift in pixels
        const EASE = 0.045; // lower = smoother/laggier follow

        function tick() {
            currentX += (targetX - currentX) * EASE;
            currentY += (targetY - currentY) * EASE;
            bgFx.style.transform = `translate(${currentX * AMPLITUDE}px, ${currentY * AMPLITUDE}px)`;
            requestAnimationFrame(tick);
        }

        requestAnimationFrame(tick);
    }

});
