frappe.provide("erpnext.utils");

// (function () {
//     const original_prepare = erpnext.utils.BarcodeScanner.prototype.prepare_item_for_scan;

//     erpnext.utils.BarcodeScanner.prototype.prepare_item_for_scan = function (
//         row,
//         item_code,
//         barcode,
//         batch_no,
//         serial_no
//     ) {
        
//         let item_data = { item_code: item_code };
//         item_data[this.qty_field] = 1; // default scanned qty
//         item_data["has_item_scanned"] = 1;

//         frappe.model.set_value(row.doctype, row.name, item_data);

//         frappe.run_serially([
//             () => this.set_batch_no(row, batch_no),
//             () => this.set_barcode(row, barcode),
//             () => this.set_serial_no(row, serial_no),
//             () => this.clean_up(),
//         ]);
//     };
// })();



(() => {
	const OriginalScanner = erpnext.utils.BarcodeScanner;

	erpnext.utils.BarcodeScanner = class FastBarcodeScanner extends OriginalScanner {

		constructor(opts) {
			super(opts);

			// FIFO Queue
			this._scan_queue = [];
			this._processing = false;

			// Duplicate Protection
			this._last_scan = null;
			this._last_scan_time = 0;

			// Ignore duplicate within 120ms
			this.DUPLICATE_DELAY = 120;
		}

		//----------------------------------------------------------------------
		// Optimized Scan Queue
		//----------------------------------------------------------------------

		process_scan() {

            if (!this.scan_barcode_field) {
                return Promise.resolve();
            }

            const input = (this.scan_barcode_field.value || "").trim();

            // Clear input immediately to allow next scan
            this.scan_barcode_field.set_value("");

            if (!input) {
                return Promise.resolve();
            }

            const now = Date.now();

            // Ignore same barcode within delay window
            if (
                this._last_scan === input &&
                now - this._last_scan_time < this.DUPLICATE_DELAY
            ) {
                return Promise.resolve();
            }

            this._last_scan = input;
            this._last_scan_time = now;

            return new Promise((resolve, reject) => {

                this._scan_queue.push({
                    input,
                    resolve,
                    reject
                });

                this.process_queue();

            });
        }

		async process_queue() {

            if (this._processing) return;

            this._processing = true;

            try {

                while (this._scan_queue.length) {

                    const job = this._scan_queue.shift();

                    try {

                        const r = await this.scan_api_call(job.input);

                        if (r && r.message) {

                            await this.prepare_item_for_scan(
                                r.message.row,
                                r.message.item_code,
                                r.message.barcode,
                                r.message.batch_no,
                                r.message.serial_no
                            );

                        }

                        job.resolve();

                    } catch (e) {

                        console.error("Barcode Scan Error", e);
                        job.reject(e);

                    }
                }

            } finally {

                this._processing = false;

            }
        }

		scan_api_call(input) {

            return frappe.call({
                method: this.scan_api,
                args: {
                    search_value: input,
                    ctx: {
                        set_warehouse: this.frm.doc.set_warehouse,
                        company: this.frm.doc.company,
                    },
                },
                freeze: false,
            })
            .catch(err => {

                console.error("Barcode API Error", err);

                throw err;

            });
        }
        

	
    		//----------------------------------------------------------------------
		// Optimized Update Table
		//----------------------------------------------------------------------

		// async update_table(data) {

		// 	if (!data || !data.item_code) {
		// 		return;
		// 	}

		// 	const row = this.items_table.find(item => {
		// 		return (
		// 			item.item_code === data.item_code &&
		// 			(!data.batch_no || item.batch_no === data.batch_no) &&
		// 			(!data.serial_no || item.serial_no === data.serial_no)
		// 		);
		// 	});

		// 	if (row) {

		// 		const qty = flt(row.qty || 0) + (data.qty || 1);

		// 		await frappe.model.set_value(
		// 			row.doctype,
		// 			row.name,
		// 			"qty",
		// 			qty
		// 		);

		// 		if (this.frm.fields_dict.items?.grid) {
		// 			this.frm.fields_dict.items.grid.refresh();
		// 		}

		// 		frappe.utils.play_sound("submit");

		// 		return row;
		// 	}

		// 	return await this.set_item(data);
		// }

		//----------------------------------------------------------------------
		// Add New Item
		//----------------------------------------------------------------------

		// async set_item(data) {

		// 	const child = this.frm.add_child(this.items_table_name);

		// 	Object.keys(data).forEach(key => {
		// 		if (child.hasOwnProperty(key)) {
		// 			child[key] = data[key];
		// 		}
		// 	});

		// 	child.qty = data.qty || 1;

		// 	this.frm.refresh_field(this.items_table_name);

		// 	frappe.utils.play_sound("submit");

		// 	return child;
		// }

		//----------------------------------------------------------------------
		// Optimized Prepare Item
		//----------------------------------------------------------------------

		prepare_item_for_scan(row, item_code, barcode, batch_no, serial_no) {

            const values = {
                item_code: item_code,
                has_item_scanned: 1
            };

            values[this.qty_field] = flt(row[this.qty_field]) || 1;


            return frappe.model
                .set_value(
                    row.doctype,
                    row.name,
                    values
                )
                .then(()=>{

                    return frappe.run_serially([
                        ()=>this.set_batch_no(row,batch_no),
                        ()=>this.set_barcode(row,barcode),
                        ()=>this.set_serial_no(row,serial_no),
                    ]);

                })
                .finally(()=>{

                    this.clean_up();

                });
        }

        validate_duplicate_serial_no(serial_no) {
            if (!serial_no) return;

            const serials = (this.dialog.get_value("serial_no") || "").split("\n");

            if (serials.includes(serial_no)) {
                frappe.throw(__("Serial No {0} already scanned", [serial_no]));
            }
        }

        async set_serial_no(row, serial_no) {
            if (!serial_no || !frappe.meta.has_field(row.doctype, this.serial_no_field)) {
                return;
            }

            const existing = row[this.serial_no_field];

            await frappe.model.set_value(
                row.doctype,
                row.name,
                this.serial_no_field,
                existing ? `${existing}\n${serial_no}` : serial_no
            );
        }
        async set_batch_no(row, batch_no) {
            if (
                batch_no &&
                frappe.meta.has_field(row.doctype, this.batch_no_field) &&
                row[this.batch_no_field] !== batch_no
            ) {
                await frappe.model.set_value(
                    row.doctype,
                    row.name,
                    this.batch_no_field,
                    batch_no
                );
            }
        }

        async set_barcode(row, barcode) {
            if (!barcode) return;

            if (frappe.meta.has_field(row.doctype, this.barcode_field)) {
                if (row[this.barcode_field] !== barcode) {
                    await frappe.model.set_value(
                        row.doctype,
                        row.name,
                        this.barcode_field,
                        barcode
                    );
                }
            } else {
                row.barcode = barcode;
            }
        }

        async set_barcode_uom(row, uom) {
            if (
                uom &&
                frappe.meta.has_field(row.doctype, this.uom_field) &&
                row[this.uom_field] !== uom
            ) {
                await frappe.model.set_value(
                    row.doctype,
                    row.name,
                    this.uom_field,
                    uom
                );
            }
        }

        is_duplicate_serial_no(row, serial_no) {
            if (!serial_no) return false;

            const serials = (row[this.serial_no_field] || "").split("\n");

            const duplicate = serials.includes(serial_no);

            if (duplicate) {
                this.show_alert(
                    __("Serial No {0} is already added", [serial_no]),
                    "orange"
                );
            }

            return duplicate;
        }

        clean_up(){

            if(this.scan_barcode_field){
                this.scan_barcode_field.set_value("");
            }

            if(this.frm && this.items_table_name){
                refresh_field(this.items_table_name);
            }

        }

    }
})();