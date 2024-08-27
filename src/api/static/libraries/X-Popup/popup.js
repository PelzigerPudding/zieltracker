function spawnPopup(contentHtml, id = null, title = null) {
    let popupHtml = $(`
        <div class="popup" ${id ? "id='" + id + "'" : ""}>
            <div class="window">
                ${title ? "<strong class='title'>" + title + "</strong>" : ""}
                <button type="button" class="close-button">
                    <i class="fa fa-close"></i>
                </button>
            </div>
        </div>
    `);

    popupHtml.find(".window").append(contentHtml);

    $("body").append(popupHtml);

    popupHtml.find(".close-button").click(e => {
        popupHtml.remove();
    });

    // Make it so, when the user clicks outside of the popup window, it closes.
    popupHtml.click(e => {
        popupHtml.remove();
    });
    popupHtml.find(".window").click(e => {
        e.stopPropagation();
    });

    return popupHtml;
}