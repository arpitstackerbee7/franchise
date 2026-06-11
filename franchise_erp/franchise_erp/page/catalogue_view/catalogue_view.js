frappe.pages['catalogue-view'].on_page_load = function(wrapper) {

    if (!frappe.user.has_role("Catalogue User")) {
        frappe.msgprint("You are not authorized to access Catalogue View");
        frappe.set_route("workspace");
        return;
    }

    frappe.ui.make_app_page({
        parent: wrapper,
        title: "Catalogue View",
        single_column: true
    });

    // CSS
    $(`<style>

    .catalog-card{
        border:1px solid #ddd;
        border-radius:12px;
        background:#fff;
        margin-bottom:25px;
        overflow:hidden;
        box-shadow:0 2px 8px rgba(0,0,0,.08);
    }

    .catalog-row{
        display:flex;
        gap:25px;
        padding:20px;
    }

    .catalog-images{
        flex:1;
        min-width:320px;
    }

    .catalog-details{
        flex:1.5;
    }

    .main-image-wrapper{
        position:relative;
    }

    .main-image{
    width:100%;
    aspect-ratio:3/4;
    object-fit:contain;
    border-radius:8px;
    background:#f8f8f8;
    border:1px solid #eee;
}

    .thumbnail-row{
        display:flex;
        gap:10px;
        margin-top:12px;
        overflow-x:auto;
    }

    .thumbnail{
    width:90px;
    height:120px;
    object-fit:cover;
    border:2px solid #ddd;
    border-radius:6px;
    cursor:pointer;
    flex-shrink:0;
}

    .thumbnail:hover{
        border-color:#000;
    }

    .slide-btn{
        position:absolute;
        top:50%;
        transform:translateY(-50%);
        width:42px;
        height:42px;
        border-radius:50%;
        border:1px solid #ccc;
        background:#fff;
        cursor:pointer;
        z-index:99;
    }

    .prev-slide{
        left:10px;
    }

    .next-slide{
        right:10px;
    }

    .item-title{
        font-size:28px;
        font-weight:700;
        margin-bottom:20px;
    }

    .item-info{
        font-size:16px;
        line-height:2;
    }

    .search-wrapper{
        padding:20px;
    }

    #item-search{
        height:50px;
        border-radius:12px;
        font-size:16px;
    }

    #search-btn{
        padding:10px 25px;
        border-radius:10px;
        margin-top:10px;
    }

    @media (max-width: 1024px){

        .catalog-row{
            flex-direction:column;
        }

        .catalog-images,
        .catalog-details{
            width:100%;
        }

    }

    @media (max-width:768px){

        .catalog-row{
            padding:15px;
        }

        .catalog-images{
            min-width:100%;
        }

        .main-image{
            max-height:450px;
        }

        .item-title{
            font-size:22px;
        }

        .item-info{
            font-size:14px;
        }

        .thumbnail{
            width:70px;
            height:90px;
        }

    }

    </style>`).appendTo("head");

    $(wrapper).html(`
        <div class="search-wrapper">

            <input
                id="item-search"
                class="form-control"
                placeholder="Search Item Code / Style"
            >

            <button
                class="btn btn-primary"
                id="search-btn"
            >
                Search
            </button>

            <hr>

            <div id="item-results"></div>

        </div>
    `);

    $(document).off("click", "#search-btn");
    $(document).off("click", ".catalog-details");
    $(document).off("click", ".thumbnail");
    $(document).off("click", ".next-slide");
    $(document).off("click", ".prev-slide");

    // SEARCH

    $(document).on("click", "#search-btn", function() {

        let keyword = $("#item-search").val();

        frappe.call({
            method: "franchise_erp.api.get_catalogue_items",
            args: {
                keyword: keyword
            },
            callback: function(r) {

                let html = "";

                (r.message || []).forEach(item => {

                    let gallery = item.gallery || [];

                    if (!gallery.length) {
                        gallery = [
                            "/assets/frappe/images/ui-states/empty-state.svg"
                        ];
                    }

                    let thumbnails = "";

                    gallery.forEach(img => {

                        thumbnails += `
                            <img
                                src="${img}"
                                class="thumbnail"
                            >
                        `;
                    });

                    html += `

                    <div class="catalog-card">

                        <div class="catalog-row">

                            <div class="catalog-images">

                                <div class="main-image-wrapper">

                                    <img
                                        src="${gallery[0]}"
                                        class="main-image"
                                    >

                                    ${
                                        gallery.length > 1
                                        ? `
                                        <button class="slide-btn prev-slide">
                                            ◀
                                        </button>

                                        <button class="slide-btn next-slide">
                                            ▶
                                        </button>
                                        `
                                        : ""
                                    }

                                </div>

                                <div class="thumbnail-row">
                                    ${thumbnails}
                                </div>

                            </div>

                            <div
                                class="catalog-details"
                                data-item="${item.name}"
                            >

                                <div class="item-title">
                                    ${item.item_name || ""}
                                </div>

                                <div class="item-info">

                                    <b>Code:</b>
                                    ${item.item_code || ""}

                                    <br>

                                    <b>Style:</b>
                                    ${item.custom_barcode_code || ""}

                                    <br>

                                    <b>Department:</b>
                                    ${item.custom_departments || ""}

                                    <br>

                                    <b>Silhouette:</b>
                                    ${item.custom_silvet || ""}

                                    <br>

                                    <b>Collection:</b>
                                    ${item.custom_group_collection || ""}

                                </div>

                            </div>

                        </div>

                    </div>
                    `;
                });

                $("#item-results").html(html);
            }
        });
    });

    // OPEN ITEM

    $(document).on("click", ".catalog-details", function() {

        let item_code = $(this).data("item");

        frappe.set_route(
            "Form",
            "Item",
            item_code
        );

    });

    // THUMBNAIL CLICK

    $(document).on("click", ".thumbnail", function(e) {

        e.stopPropagation();

        let img = $(this).attr("src");

        $(this)
            .closest(".catalog-images")
            .find(".main-image")
            .attr("src", img);

    });

    // NEXT

    $(document).on("click", ".next-slide", function(e) {

        e.preventDefault();
        e.stopPropagation();

        let wrapper = $(this)
            .closest(".catalog-images");

        let thumbs = wrapper.find(".thumbnail");

        let mainImage = wrapper.find(".main-image");

        let currentSrc = mainImage.attr("src");

        let currentIndex = 0;

        thumbs.each(function(i){

            if($(this).attr("src") === currentSrc){
                currentIndex = i;
            }

        });

        let nextIndex =
            (currentIndex + 1) % thumbs.length;

        mainImage.attr(
            "src",
            $(thumbs[nextIndex]).attr("src")
        );

    });

    // PREVIOUS

    $(document).on("click", ".prev-slide", function(e) {

        e.preventDefault();
        e.stopPropagation();

        let wrapper = $(this)
            .closest(".catalog-images");

        let thumbs = wrapper.find(".thumbnail");

        let mainImage = wrapper.find(".main-image");

        let currentSrc = mainImage.attr("src");

        let currentIndex = 0;

        thumbs.each(function(i){

            if($(this).attr("src") === currentSrc){
                currentIndex = i;
            }

        });

        let prevIndex =
            (currentIndex - 1 + thumbs.length)
            % thumbs.length;

        mainImage.attr(
            "src",
            $(thumbs[prevIndex]).attr("src")
        );

    });

};