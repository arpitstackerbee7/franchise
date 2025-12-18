frappe.ui.form.on('Item', {
    
    onload(frm) {
        set_item_group_query(frm);
    },
    refresh(frm) {
        set_item_group_query(frm);
    }
});

function set_item_group_query(frm) {
   frm.set_query('custom_silvet', () => {
            return {
                query: 'franchise_erp.api.item_group.all_item_group_for_silvet'
            };
        });
}
