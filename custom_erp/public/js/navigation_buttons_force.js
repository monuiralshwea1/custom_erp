// ≈Ã»«— ≈÷«›… √“—«— «· ‰ﬁ· - Force Navigation Buttons
// Â–« «·„·› Ì÷„‰ ŸÂÊ— «·√“—«— Õ Ï ·Ê ﬂ«‰  Â‰«ﬂ „‘«ﬂ· ›Ì «· Õ„Ì·

(function () {
    'use strict';

    console.log('??  Õ„Ì· √“—«— «· ‰ﬁ· «·≈Ã»«—Ì…...');

    // ≈‰‘«¡ namespace ≈–« ·„ Ìﬂ‰ „ÊÃÊœ«
    window.custom_erp = window.custom_erp || {};
    window.custom_erp.navigation = window.custom_erp.navigation || {
        history: [],
        current_index: -1,
        navigating: false
    };

    // œÊ«· «· ‰ﬁ·
    window.custom_erp.navigation.add_to_history = function (route) {
        this.history = this.history.slice(0, this.current_index + 1);
        this.history.push(route);
        this.current_index = this.history.length - 1;

        if (this.history.length > 50) {
            this.history.shift();
            this.current_index--;
        }

        this.update_buttons();
    };

    window.custom_erp.navigation.go_back = function () {
        if (this.current_index > 0) {
            this.current_index--;
            const route = this.history[this.current_index];
            this.navigating = true;

            if (window.frappe && window.frappe.set_route) {
                window.frappe.set_route(route);
            } else {
                window.location.hash = '#' + route;
            }

            setTimeout(() => {
                this.navigating = false;
                this.update_buttons();
            }, 100);
        }
    };

    window.custom_erp.navigation.go_forward = function () {
        if (this.current_index < this.history.length - 1) {
            this.current_index++;
            const route = this.history[this.current_index];
            this.navigating = true;

            if (window.frappe && window.frappe.set_route) {
                window.frappe.set_route(route);
            } else {
                window.location.hash = '#' + route;
            }

            setTimeout(() => {
                this.navigating = false;
                this.update_buttons();
            }, 100);
        }
    };

    window.custom_erp.navigation.update_buttons = function () {
        const back_btn = document.querySelector('.custom-nav-back');
        const forward_btn = document.querySelector('.custom-nav-forward');

        if (back_btn) {
            if (this.current_index > 0) {
                back_btn.classList.remove('disabled');
                back_btn.disabled = false;
            } else {
                back_btn.classList.add('disabled');
                back_btn.disabled = true;
            }
        }

        if (forward_btn) {
            if (this.current_index < this.history.length - 1) {
                forward_btn.classList.remove('disabled');
                forward_btn.disabled = false;
            } else {
                forward_btn.classList.add('disabled');
                forward_btn.disabled = true;
            }
        }
    };

    // ≈÷«›… CSS „»«‘—…
    function addNavigationCSS() {
        if (document.querySelector('#custom-nav-css')) return;

        const style = document.createElement('style');
        style.id = 'custom-nav-css';
        style.textContent = `
            .custom-navigation-buttons {
                display: flex !important;
                align-items: center;
                gap: 5px;
                margin: 0 10px;
            }
            .custom-nav-back, .custom-nav-forward {
                background-color: #f8f9fa !important;
                border: 1px solid #dee2e6 !important;
                color: #495057 !important;
                padding: 4px 8px !important;
                border-radius: 4px !important;
                font-size: 14px !important;
                min-width: 32px;
                height: 32px;
                display: flex;
                align-items: center;
                justify-content: center;
                transition: all 0.2s ease;
            }
            .custom-nav-back:hover:not(.disabled), .custom-nav-forward:hover:not(.disabled) {
                background-color: #007bff !important;
                border-color: #007bff !important;
                color: white !important;
            }
            .custom-nav-back.disabled, .custom-nav-forward.disabled {
                background-color: #e9ecef !important;
                color: #6c757d !important;
                cursor: not-allowed !important;
                opacity: 0.6;
            }
        `;
        document.head.appendChild(style);
    }

    // œ«·… ≈÷«›… «·√“—«—
    function forceAddNavigationButtons() {
        console.log('?? ≈÷«›… √“—«— «· ‰ﬁ· «·≈Ã»«—Ì…...');

        // ≈÷«›… CSS √Ê·«
        addNavigationCSS();

        // ≈“«·… «·√“—«— «·„ÊÃÊœ…
        const existing = document.querySelector('.custom-navigation-buttons');
        if (existing) {
            existing.remove();
        }

        // «·»ÕÀ ⁄‰ „ﬂ«‰ „‰«”»
        let container = document.querySelector('.form-inline[role="search"]');
        if (!container) container = document.querySelector('.navbar .justify-content-end');
        if (!container) container = document.querySelector('.navbar .container');
        if (!container) container = document.querySelector('header .container');
        if (!container) container = document.querySelector('.navbar');
        if (!container) container = document.querySelector('header');

        if (!container) {
            console.log('? ·„ Ì „ «·⁄ÀÊ— ⁄·Ï „ﬂ«‰ „‰«”»');
            return false;
        }

        // ≈‰‘«¡ «·√“—«—
        const buttonsHTML = `
            <div class="custom-navigation-buttons" style="display: flex; align-items: center; gap: 5px; margin: 0 10px;">
                <button class="btn btn-sm btn-outline-secondary custom-nav-back" 
                        title="—ÃÊ⁄ ··’›Õ… «·”«»ﬁ…" 
                        type="button"
                        style="padding: 4px 8px; border-radius: 4px; min-width: 32px; height: 32px;">
                    <i class="fa fa-arrow-right" style="font-size: 14px;"></i>
                </button>
                <button class="btn btn-sm btn-outline-secondary custom-nav-forward" 
                        title="«·–Â«» ··’›Õ… «· «·Ì…" 
                        type="button"
                        style="padding: 4px 8px; border-radius: 4px; min-width: 32px; height: 32px;">
                    <i class="fa fa-arrow-left" style="font-size: 14px;"></i>
                </button>
            </div>
        `;

        // ≈÷«›… «·√“—«—
        if (container.classList.contains('form-inline')) {
            container.insertAdjacentHTML('afterbegin', buttonsHTML);
        } else {
            container.insertAdjacentHTML('beforeend', buttonsHTML);
        }

        // —»ÿ «·√Õœ«À
        const backBtn = document.querySelector('.custom-nav-back');
        const forwardBtn = document.querySelector('.custom-nav-forward');

        if (backBtn) {
            backBtn.addEventListener('click', function (e) {
                e.preventDefault();
                e.stopPropagation();
                window.custom_erp.navigation.go_back();
            });
        }

        if (forwardBtn) {
            forwardBtn.addEventListener('click', function (e) {
                e.preventDefault();
                e.stopPropagation();
                window.custom_erp.navigation.go_forward();
            });
        }

        //  ÕœÌÀ Õ«·… «·√“—«—
        window.custom_erp.navigation.update_buttons();

        console.log('?  „ ≈÷«›… √“—«— «· ‰ﬁ· »‰Ã«Õ');
        return true;
    }

    // „Õ«Ê·… ≈÷«›… «·√“—«— ⁄‰œ  Õ„Ì· «·’›Õ…
    function initButtons() {
        let attempts = 0;
        const maxAttempts = 20;

        const tryAdd = function () {
            attempts++;
            console.log(`?? „Õ«Ê·… ${attempts}/${maxAttempts}`);

            if (forceAddNavigationButtons()) {
                return; // ‰ÃÕ  «·≈÷«›…
            }

            if (attempts < maxAttempts) {
                setTimeout(tryAdd, 1000);
            } else {
                console.log('?? ›‘· ›Ì ≈÷«›… «·√“—«— »⁄œ Ã„Ì⁄ «·„Õ«Ê·« ');
            }
        };

        tryAdd();
    }

    // »œ¡ «· ‘€Ì·
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initButtons);
    } else {
        initButtons();
    }

    // „—«ﬁ»…  €ÌÌ— «·’›Õ« 
    function monitorRouteChanges() {
        let currentPath = window.location.pathname + window.location.hash;

        setInterval(function () {
            const newPath = window.location.pathname + window.location.hash;
            if (newPath !== currentPath && !window.custom_erp.navigation.navigating) {
                currentPath = newPath;
                window.custom_erp.navigation.add_to_history(newPath);

                // ≈⁄«œ… ≈÷«›… «·√“—«— ≈–« «Œ › 
                setTimeout(function () {
                    if (!document.querySelector('.custom-navigation-buttons')) {
                        forceAddNavigationButtons();
                    }
                }, 500);
            }
        }, 1000);
    }

    // »œ¡ „—«ﬁ»… «· €ÌÌ—« 
    setTimeout(monitorRouteChanges, 2000);

})();
