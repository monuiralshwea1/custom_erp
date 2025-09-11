// ≈÷«›… √“—«— «· ‰ﬁ· ›Ì ‘—Ìÿ «·√œÊ«  «·⁄·ÊÌ
frappe.provide("custom_erp.navigation");

// „ €Ì—«  ·  »⁄  «—ÌŒ «· ‰ﬁ·
custom_erp.navigation = {
    history: [],
    current_index: -1,
    navigating: false, // ·„‰⁄ ≈÷«›… «· ‰ﬁ· ⁄»— «·√“—«— ·· «—ÌŒ

    // ≈÷«›… ’›Õ… ÃœÌœ… ·· «—ÌŒ
    add_to_history: function (route) {
        // ≈“«·… «·’›Õ«  «· Ì  √ Ì »⁄œ «·„Ê÷⁄ «·Õ«·Ì (›Ì Õ«·… «·—ÃÊ⁄ À„ «·–Â«» ·’›Õ… ÃœÌœ…)
        this.history = this.history.slice(0, this.current_index + 1);

        // ≈÷«›… «·’›Õ… «·ÃœÌœ…
        this.history.push(route);
        this.current_index = this.history.length - 1;

        // «·Õ›«Ÿ ⁄·Ï Õœ √ﬁ’Ï 50 ’›Õ… ›Ì «· «—ÌŒ
        if (this.history.length > 50) {
            this.history.shift();
            this.current_index--;
        }

        this.update_buttons();
    },

    // «·—ÃÊ⁄ ··’›Õ… «·”«»ﬁ…
    go_back: function () {
        if (this.current_index > 0) {
            this.current_index--;
            const route = this.history[this.current_index];
            this.navigating = true; // „‰⁄ ≈÷«›… Â–« «· ‰ﬁ· ·· «—ÌŒ
            frappe.set_route(route);
            setTimeout(() => {
                this.navigating = false;
                this.update_buttons();
            }, 100);
        }
    },

    // «·–Â«» ··’›Õ… «· «·Ì…
    go_forward: function () {
        if (this.current_index < this.history.length - 1) {
            this.current_index++;
            const route = this.history[this.current_index];
            this.navigating = true; // „‰⁄ ≈÷«›… Â–« «· ‰ﬁ· ·· «—ÌŒ
            frappe.set_route(route);
            setTimeout(() => {
                this.navigating = false;
                this.update_buttons();
            }, 100);
        }
    },

    //  ÕœÌÀ Õ«·… «·√“—«—
    update_buttons: function () {
        const back_btn = $('.custom-nav-back');
        const forward_btn = $('.custom-nav-forward');

        //  ÕœÌÀ “— «·—ÃÊ⁄
        if (this.current_index > 0) {
            back_btn.removeClass('disabled').prop('disabled', false);
        } else {
            back_btn.addClass('disabled').prop('disabled', true);
        }

        //  ÕœÌÀ “— «· «·Ì
        if (this.current_index < this.history.length - 1) {
            forward_btn.removeClass('disabled').prop('disabled', false);
        } else {
            forward_btn.addClass('disabled').prop('disabled', true);
        }
    }
};

// ≈÷«›… √“—«— «· ‰ﬁ· ⁄‰œ  Õ„Ì· «·’›Õ…
$(document).ready(function () {
    console.log('?? »œ¡  Õ„Ì· √“—«— «· ‰ﬁ·...');

    // «‰ Ÿ«—  Õ„Ì· ‘—Ìÿ «·√œÊ« 
    setTimeout(function () {
        add_navigation_buttons();
    }, 1000);

    // „Õ«Ê·… ≈÷«›… «·√“—«— ﬂ· À«‰Ì Ì‰ ≈–« ·„  ŸÂ—
    let attempts = 0;
    const max_attempts = 10;
    const check_buttons = setInterval(function () {
        attempts++;
        if ($('.custom-navigation-buttons').length === 0 && attempts < max_attempts) {
            console.log(`?? ≈⁄«œ… „Õ«Ê·… ≈÷«›… √“—«— «· ‰ﬁ·... («·„Õ«Ê·… ${attempts}/${max_attempts})`);
            add_navigation_buttons();
        } else {
            clearInterval(check_buttons);
            if (attempts >= max_attempts) {
                console.log('??  „ «·Ê’Ê· ··Õœ «·√ﬁ’Ï „‰ «·„Õ«Ê·« ');
            }
        }
    }, 2000);

    // ≈÷«›… «·’›Õ… «·Õ«·Ì… ·· «—ÌŒ ⁄‰œ «· Õ„Ì· «·√Ê·
    const initial_route = frappe.get_route_str();
    if (initial_route) {
        custom_erp.navigation.add_to_history(initial_route);
    }
});

// „—«ﬁ»…  €ÌÌ— «·’›Õ«  »«” Œœ«„ ‰Ÿ«„ Frappe
frappe.router.on('change', function () {
    setTimeout(function () {
        const current_route = frappe.get_route_str();

        //  Ã«Â· «· ‰ﬁ· ≈–« ﬂ«‰ ⁄»— √“—«—‰«
        if (!custom_erp.navigation.navigating &&
            current_route &&
            current_route !== custom_erp.navigation.history[custom_erp.navigation.current_index]) {
            custom_erp.navigation.add_to_history(current_route);
        }

        // ≈⁄«œ… ≈÷«›… «·√“—«— ≈–« ·„  ﬂ‰ „ÊÃÊœ…
        if ($('.custom-navigation-buttons').length === 0) {
            add_navigation_buttons();
        }
    }, 500);
});

// ≈÷«›… „—«ﬁ» ≈÷«›Ì ·· √ﬂœ „‰ ŸÂÊ— «·√“—«—
$(document).on('DOMContentLoaded', function () {
    setTimeout(add_navigation_buttons, 2000);
});

// „—«ﬁ»…  Õ„Ì· «·‰«›–…
$(window).on('load', function () {
    setTimeout(add_navigation_buttons, 1000);
});

function add_navigation_buttons() {
    console.log('?? «·»ÕÀ ⁄‰ „ﬂ«‰ ·≈÷«›… √“—«— «· ‰ﬁ·...');

    // «·»ÕÀ ⁄‰ ‘—Ìÿ «·»ÕÀ ›Ì √„«ﬂ‰ „Œ ·›…
    let search_container = $('.form-inline[role="search"]');
    console.log('?? ‘—Ìÿ «·»ÕÀ:', search_container.length);

    // ≈–« ·„ ‰Ãœ ‘—Ìÿ «·»ÕÀ° ‰»ÕÀ ›Ì √„«ﬂ‰ √Œ—Ï
    if (search_container.length === 0) {
        search_container = $('.navbar .justify-content-end');
        console.log('?? navbar justify-content-end:', search_container.length);
    }

    // ≈–« ·„ ‰Ãœ √Ì „ﬂ«‰ „‰«”»° ‰»ÕÀ ›Ì «·‹ navbar
    if (search_container.length === 0) {
        search_container = $('.navbar .container');
        console.log('?? navbar container:', search_container.length);
    }

    // «·»ÕÀ ›Ì header
    if (search_container.length === 0) {
        search_container = $('header .container');
        console.log('?? header container:', search_container.length);
    }

    // «·»ÕÀ ›Ì √Ì navbar „ÊÃÊœ
    if (search_container.length === 0) {
        search_container = $('.navbar');
        console.log('?? √Ì navbar:', search_container.length);
    }

    if (search_container.length === 0) {
        console.log('? ·„ Ì „ «·⁄ÀÊ— ⁄·Ï „ﬂ«‰ „‰«”» ·≈÷«›… «·√“—«—');
        return;
    }

    // ≈“«·… «·√“—«— ≈–« ﬂ«‰  „ÊÃÊœ… „”»ﬁ«
    $('.custom-navigation-buttons').remove();

    // ≈‰‘«¡ Õ«ÊÌ… «·√“—«—
    const nav_buttons = $(`
        <div class="custom-navigation-buttons">
            <button class="btn btn-sm btn-outline-secondary custom-nav-back"
                    title="—ÃÊ⁄ ··’›Õ… «·”«»ﬁ…"
                    type="button">
                <i class="fa fa-arrow-right"></i>
            </button>
            <button class="btn btn-sm btn-outline-secondary custom-nav-forward"
                    title="«·–Â«» ··’›Õ… «· «·Ì…"
                    type="button">
                <i class="fa fa-arrow-left"></i>
            </button>
        </div>
    `);

    // ≈÷«›… «·√“—«— ›Ì «·„ﬂ«‰ «·„‰«”»
    if (search_container.hasClass('form-inline')) {
        search_container.prepend(nav_buttons);
    } else {
        search_container.append(nav_buttons);
    }

    // —»ÿ «·√Õœ«À
    $('.custom-nav-back').off('click').on('click', function (e) {
        e.preventDefault();
        e.stopPropagation();
        custom_erp.navigation.go_back();
    });

    $('.custom-nav-forward').off('click').on('click', function (e) {
        e.preventDefault();
        e.stopPropagation();
        custom_erp.navigation.go_forward();
    });

    //  ÕœÌÀ Õ«·… «·√“—«—
    custom_erp.navigation.update_buttons();

    console.log('?  „ ≈÷«›… √“—«— «· ‰ﬁ· »‰Ã«Õ');
}

frappe.ui.form.on('*', {
    refresh(frm) {
        // ≈ŸÂ«— «·“— œ«∆„«
        frm.add_custom_button(__('ÃœÌœ'), function () {
            frappe.set_route("Form", frm.doctype, null);  // › Õ ‰„Ê–Ã ÃœÌœ „‰ ‰›” «·‰Ê⁄
        });

        //  ⁄œÌ· ‘ﬂ· «·“— (·Ê‰ √“—ﬁ ÊŒÿ √»Ì÷)
        setTimeout(() => {
            const buttons = document.querySelectorAll('button:contains("ÃœÌœ")');
            buttons.forEach(btn => {
                btn.style.backgroundColor = '#007bff';
                btn.style.color = 'white';
                btn.style.border = 'none';
                btn.style.padding = '6px 12px';
                btn.style.borderRadius = '4px';
            });
        }, 100);
    }
});
frappe.listview_settings['Purchase Invoice'] = {
    onload: function (listview) {
        const pos_profile = "‰ﬁœ";
        const supplier_name = "„Ê—œ ‰ﬁœÌ";

        // ≈‰‘«¡ ›« Ê—… „‘ —Ì«  ‰ﬁœÌ…
        async function create_cash_purchase_invoice() {
            try {
                const profile_doc = await frappe.db.get_doc("POS Profile", pos_profile);
                const cash_account = profile_doc.payments.find(p => p.mode_of_payment === "Cash")?.account;

                const new_invoice = frappe.model.get_new_doc('Purchase Invoice');
                new_invoice.is_paid = 1;
                new_invoice.pos_profile = pos_profile;
                new_invoice.supplier = supplier_name;
                new_invoice.mode_of_payment = "Cash"

                new_invoice.payments = [{
                    mode_of_payment: "Cash",
                    account: cash_account,
                    amount: 0
                }];

                frappe.set_route('Form', 'Purchase Invoice', new_invoice.name);
            } catch (e) {
                console.error(e);
                frappe.msgprint("ÕœÀ Œÿ√ √À‰«¡ ≈‰‘«¡ «·›« Ê—….");
            }
        }

        // ≈‰‘«¡ ›« Ê—… „— Ã⁄ ÌœÊÌ«
        async function create_purchase_return_from_invoice(docname) {
            try {
                const source = await frappe.db.get_doc("Purchase Invoice", docname);

                if (source.is_return) {
                    frappe.msgprint("? ·« Ì„ﬂ‰ ≈‰‘«¡ „— Ã⁄ ·›« Ê—… ÂÌ √’·« „— Ã⁄.");
                    return;
                }

                // «·›Ê« Ì— «·”«»ﬁ… «·„— Ã⁄…
                const returned_invoices = await frappe.db.get_list("Purchase Invoice", {
                    filters: {
                        docstatus: 1,
                        is_return: 1,
                        return_against: docname
                    },
                    fields: ["name"]
                });

                let returned_items = {};
                for (let inv of returned_invoices) {
                    let return_doc = await frappe.db.get_doc("Purchase Invoice", inv.name);
                    for (let item of return_doc.items) {
                        if (!returned_items[item.item_code]) {
                            returned_items[item.item_code] = 0;
                        }
                        returned_items[item.item_code] += Math.abs(item.qty);
                    }
                }

                let new_doc = frappe.model.get_new_doc('Purchase Invoice');
                new_doc.is_return = 1;
                new_doc.return_against = source.name;
                new_doc.supplier = source.supplier;
                new_doc.posting_date = frappe.datetime.nowdate();
                new_doc.posting_time = frappe.datetime.now_time();
                new_doc.items = [];

                for (let item of source.items) {
                    const total_qty = item.qty;
                    const returned_qty = returned_items[item.item_code] || 0;
                    const remaining_qty = total_qty - returned_qty;

                    if (remaining_qty > 0) {
                        new_doc.items.push({
                            item_code: item.item_code,
                            item_name: item.item_name,
                            qty: -remaining_qty,
                            rate: item.rate,
                            uom: item.uom,
                            conversion_factor: item.conversion_factor,
                            warehouse: item.warehouse
                        });
                    }
                }

                if (new_doc.items.length === 0) {
                    frappe.msgprint("?? ﬂ· √’‰«› Â–Â «·›« Ê—…  „ ≈—Ã«⁄Â« „”»ﬁ«.");
                    return;
                }

                frappe.model.sync(new_doc);
                frappe.set_route("Form", "Purchase Invoice", new_doc.name);

            } catch (e) {
                console.error(e);
                frappe.msgprint("ÕœÀ Œÿ√ √À‰«¡ ≈‰‘«¡ ›« Ê—… «·„— Ã⁄.");
            }
        }

        // “— „— Ã⁄ „‘ —Ì« 
        listview.page.add_inner_button(__('?? „— Ã⁄ „‘ —Ì« '), async function () {
            const selected = listview.get_checked_items();

            if (selected.length === 0) {
                const new_doc = frappe.model.get_new_doc('Purchase Invoice');
                new_doc.is_return = 1;
                frappe.set_route('Form', 'Purchase Invoice', new_doc.name);
                return;
            }

            if (selected.length > 1) {
                frappe.msgprint(__('Ì—ÃÏ  ÕœÌœ ›« Ê—… Ê«Õœ… ›ﬁÿ ·≈‰‘«¡ „— Ã⁄.'));
                return;
            }

            const docname = selected[0].name;
            await create_purchase_return_from_invoice(docname);
        });

        // “— ≈‰‘«¡ ›« Ê—… „‘ —Ì«  ‰ﬁœÌ…
        listview.page.add_inner_button(__('?? ≈÷«›… ›« Ê—… „‘ —Ì«  ‰ﬁœÌ…'), function () {
            create_cash_purchase_invoice();
        });
    }
};
// frappe.ui.form.on('Purchase Invoice', {
//     onload: function(frm) {
//         if (frm.doc.is_return) {
//             frm.set_df_property('payments_section', 'hidden', 1);
//             frm.set_df_property('base_paid_amount', 'hidden', 1);
//             frm.set_df_property('paid_amount', 'hidden', 1);
//             frm.set_df_property('change_amount', 'hidden', 1);
//             frm.set_df_property('pos_profile', 'hidden', 1);
//             frm.set_df_property('mode_of_payment', 'hidden', 1);
//             frm.set_df_property('total_advance', 'hidden', 1);
//             frm.set_df_property('write_off_amount', 'hidden', 1);
//             frm.set_df_property('return_against', 'hidden', 0);
//             frm.set_df_property('apply_tdst', 'hidden', 0);

//         } else {
//             frm.set_df_property('payments_section', 'hidden', 0);
//             frm.set_df_property('base_paid_amount', 'hidden', 0);
//             frm.set_df_property('paid_amount', 'hidden', 0);
//             frm.set_df_property('change_amount', 'hidden', 0);
//             frm.set_df_property('pos_profile', 'hidden', 0);
//             frm.set_df_property('mode_of_payment', 'hidden', 0);
//             frm.set_df_property('total_advance', 'hidden', 0);
//             frm.set_df_property('write_off_amount', 'hidden', 0);
//             frm.set_df_property('is_return', 'hidden', true);
//             frm.set_df_property('update_billed_amount_in_purchase_order', 'hidden', true);
//             frm.set_df_property('is_debit_note', 'hidden', true);
//             frm.set_df_property('apply_tdst', 'hidden', 0);
//         }
//     }
// });
frappe.ui.form.on('Purchase Invoice', {
    onload: function (frm) {
        // ⁄—÷/≈Œ›«¡ «·ÕﬁÊ· Õ”» ‰Ê⁄ «·›« Ê—…
        if (frm.doc.is_return) {
            frm.set_df_property('payments_section', 'hidden', 1);
            frm.set_df_property('base_paid_amount', 'hidden', 1);
            frm.set_df_property('paid_amount', 'hidden', 1);
            frm.set_df_property('change_amount', 'hidden', 1);
            frm.set_df_property('pos_profile', 'hidden', 1);
            frm.set_df_property('mode_of_payment', 'hidden', 1);
            frm.set_df_property('total_advance', 'hidden', 1);
            frm.set_df_property('write_off_amount', 'hidden', 1);
            frm.set_df_property('return_against', 'hidden', 0);
        } else {
            frm.set_df_property('payments_section', 'hidden', 0);
            frm.set_df_property('base_paid_amount', 'hidden', 0);
            frm.set_df_property('paid_amount', 'hidden', 0);
            frm.set_df_property('change_amount', 'hidden', 0);
            frm.set_df_property('pos_profile', 'hidden', 0);
            frm.set_df_property('mode_of_payment', 'hidden', 0);
            frm.set_df_property('total_advance', 'hidden', 0);
            frm.set_df_property('write_off_amount', 'hidden', 0);
            frm.set_df_property('is_return', 'hidden', true);
            frm.set_df_property('update_billed_amount_in_purchase_order', 'hidden', true);
            frm.set_df_property('is_debit_note', 'hidden', true);
        }

        // ? “— ÃœÌœ (¬Ã·)
        frm.add_custom_button('?? ÃœÌœ (¬Ã·)', () => {
            frappe.new_doc('Purchase Invoice');
        });

        // ?? “— ÃœÌœ (‰ﬁœ)
        frm.add_custom_button('?? ÃœÌœ (‰ﬁœ)', async () => {
            const pos_profile = "‰ﬁœ"; // ⁄œ·Â Õ”» ‰Ÿ«„ﬂ
            const supplier_name = "„Ê—œ ‰ﬁœÌ"; // ⁄œ·Â Õ”» «·„Ê—œ «·‰ﬁœÌ

            try {
                const profile_doc = await frappe.db.get_doc("POS Profile", pos_profile);
                const cash_account = profile_doc.payments.find(p => p.mode_of_payment === "Cash")?.account;

                const new_invoice = frappe.model.get_new_doc('Purchase Invoice');
                new_invoice.is_pos = 1;
                new_invoice.is_paid = 1; // ‰ﬁœ
                new_invoice.pos_profile = pos_profile;
                new_invoice.supplier = supplier_name;
                new_invoice.mode_of_payment = "Cash"


                // new_invoice.payments = [{
                //     mode_of_payment: "Cash",
                //     account: cash_account,
                //     amount: 0
                // }];

                frappe.set_route('Form', 'Purchase Invoice', new_invoice.name);
            } catch (e) {
                console.error(e);
                frappe.msgprint("ÕœÀ Œÿ√ √À‰«¡ ≈‰‘«¡ «·›« Ê—… «·‰ﬁœÌ….");
            }
        });
    }
});
