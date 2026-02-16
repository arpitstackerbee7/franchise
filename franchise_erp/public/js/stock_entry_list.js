frappe.listview_settings['Stock Entry'] = {
  add_fields: ['custom_status'],  // make sure it's in list view

  get_indicator: function (doc) {
    let status = null;  

    if (doc.docstatus === 2) {
      status = 'Cancelled';
    } else if (doc.docstatus === 0) {
      status = 'Draft';
    } else {
      status = doc.custom_status || 'Submitted';
    }

    const color = get_color(status);

    return [__(status), color, `custom_status,=,${status}`];
  }
};

function get_color(status) {
  const colors = {
    'In Transit': 'yellow',
    'Transferred': 'green',
    'Delivered': 'orange',
    'Fully Submitted': 'purple',
    'Submitted': 'cyan',
    'Partially Delivered': 'blue',
    'Draft': 'red',
    'Cancelled': 'red'
  };
  return colors[status] || 'gray';
}