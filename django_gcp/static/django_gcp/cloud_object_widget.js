if ($ === undefined) $ = django.jQuery;


function getWrapper(e, $) {
  // Get the current field wrapper
  const wrapper = $(e.target).closest(".gcp-wrapper");
  return wrapper
}

function getValue(wrapper) {
  // Get the current value as json
  const input = wrapper.find("input[type=hidden]");
  const value = JSON.parse(input.val()) || {}
  return value
}

function setValue(wrapper, value) {
  // Set the current value as stringified JSON
  const stringified = value ? JSON.stringify(value) : "{}"
  console.log('Setting value', stringified)
  wrapper.find("input[type=hidden]").val(stringified);
}

function clearExisting(wrapper) {
  const value = getValue(wrapper);
  // Remove ["path"] from the current object, handling current object being empty
  // Leave "_tmp_path" and "name" there (don't interfere with a file selection)
  if (value.path) {
    delete value.path;
    setValue(wrapper, value);
  }
  // Add strikethrough and warning colour to the existing path text
  wrapper.find(".gcp-existing-path").addClass("gcp-warning");
  // Alter button to "Reset"
  wrapper.find(".gcp-clear-restore-existing").text("Reset");
}

function restoreExisting(wrapper) {
  console.log('reset')
  // Reset to the original value (either {} or {"path": "whatever"})
  const value = {}
  const existingPath = wrapper.data("existing-path")
  const hasExistingPath = existingPath && existingPath.length > 0
  if (hasExistingPath) {
    value.path = existingPath
  }
  setValue(wrapper, value)
  // Remove strikethrough and warning colour from existing path text
  wrapper.find(".gcp-existing-path").removeClass("gcp-warning");
  // Update the reset button
  const resetButton = wrapper.find(".gcp-clear-restore-existing")
  resetButton.text("Clear existing");
  // If there is no existing path, disable the clear existing button
  if (hasExistingPath) {
    resetButton.removeClass("gcp-disabled").prop("disabled", false);
  } else {
    resetButton.addClass("gcp-disabled").prop("disabled", true);
  }
  // Since this also clears the selection, disable the clear selection button
  wrapper.find(".gcp-clear-selected").addClass("gcp-disabled").prop("disabled", true);
}

function clearSelected(wrapper) {
  // Remove the ingress from the value
  const value = getValue(wrapper)
  delete value._tmp_path
  delete value.name
  delete value.attributes
  setValue(wrapper, value)
  // Remove the file selection from the input
  wrapper.find(".gcp-file-input").val("");
  // Update shown selected value
  wrapper.find(".gcp-selected-name").text("");
  // Update button text to "Select file"
  wrapper.find(".gcp-select-label").text("Select file");
  wrapper.find(".gcp-clear-selected").addClass("gcp-disabled hidden").prop("disabled", true);
}

function addSelected(wrapper, name, contentType) {
  // Add "_tmp_path" and "name" to the input
  const value = {
    "_tmp_path": wrapper.data("ingress-path"),
    "name": name,
    "attributes": {"content_type": contentType}
  }
  setValue(wrapper, value)
  // [FROM CLEAREXISTING] Add strikethrough and warning colour to the existing path text
  wrapper.find(".gcp-existing-path").addClass("gcp-warning");
  // [FROM CLEAREXISTING] Alter button to "Reset"
  wrapper.find(".gcp-clear-restore-existing").val("Reset");
  // Update shown selected value
  wrapper.find(".gcp-selected-name").text(name);
  // Update button text to "Select other"
  wrapper.find(".gcp-select-label").text("Select other");
  // Enable user to clear selection
  wrapper.find(".gcp-clear-selected").removeClass("gcp-disabled hidden").prop("disabled", false);
}

function hasSelected(wrapper) {
  // Return true is a file is selected
  const file_selected = $(wrapper).find(".gcp-selected-name").text() !== "";
  return file_selected
}





// function updateVisibility(wrapper, file_selected, has_existing) {
//   wrapper.find(".gcp-clear-selection").toggle(file_selected);
//   if (!file_selected) {
//     wrapper.find(".gcp-selected-name").text("");
//     wrapper.find(".gcp-select-label").text("Select file");
//     wrapper.find(".gcp-clear-restore-existing").addClass("gcp-disabled");
//     wrapper.find(".gcp-clear-restore-existing").prop('disabled', true);
//   } else {
//     wrapper.find(".gcp-select-label").text("Select a different file")
//     if (has_existing) {
//       wrapper.find(".gcp-clear-restore-existing").removeClass("gcp-disabled")
//       wrapper.find(".gcp-clear-restore-existing").prop('disabled', false);
//     }
//   }
// }

$(document).ready(function($) {
  // Update the visibility of form field elements
  $(".gcp-wrapper").each(function(i, wrapper) {
    restoreExisting($(wrapper));
    clearSelected($(wrapper));
  });

  // Multiple widgets may exist on the page, but we only need one overlay
  $(".gcp-overlay")
    .slice(1)
    .remove(); 
  $(".gcp-overlay").appendTo("body");

  // Handle selection of a file
  $(".gcp-file-input").on("change", function(e) {
    const wrapper = getWrapper(e, $);
    // Get the selected file (it's a single file select dialog so there will be 0 or 1)
    if (e.target.files.length === 1) {
      var file = e.target.files[0];
      addSelected(wrapper, file.name, file.type)
    }
  });

  $(".gcp-clear-restore-existing").on("click", function(e) {
    const wrapper = getWrapper(e, $)
    console.log('CLICKED', wrapper.find(".gcp-clear-restore-existing").text(), wrapper.find(".gcp-clear-restore-existing").text() === "Clear existing")
    if (wrapper.find(".gcp-clear-restore-existing").text() === "Clear existing") {
      clearExisting(wrapper)
    } else {
      restoreExisting(wrapper)
    }});

  $(".gcp-clear-selected").on("click", function(e) {
    const wrapper = getWrapper(e, $)
    clearSelected(wrapper)
  });

  $("form").submit(function(submitEvent) {

    if (window.gcp_uploads_complete === true) return true; // Don't intercept submission

    // Get a list of the uploads required
    var wrappers_to_upload = [];
    $(submitEvent.target)
      .find(".gcp-wrapper")
      .each(function(i, wrapper) {
        if (
          $(wrapper)
            .find(".gcp-file-input")
            .get(0).files.length === 1
        )
          wrappers_to_upload.push(wrapper);
      });

    // Submit immediately if no uploads are required
    if (wrappers_to_upload.length === 0) return true;

    // Set the overlay and upload counter
    window.gcp_number_of_files = wrappers_to_upload.length;
    $(".gcp-overlay").css("display", "flex");

    // Intercept submission (to be re-triggered on completion of uploads)
    submitEvent.preventDefault();

    $.each(wrappers_to_upload, function(i, element) {
      const wrapper = $(element)
      // var field = wrapper.find("input[type=hidden]");
      var file = wrapper.find(".gcp-file-input").get(0).files[0];
      const signed_ingress_url = wrapper.data("signed-ingress-url")
      const max_size_bytes = wrapper.data("max-size-bytes")
      const headers = {}
      if (max_size_bytes !== 0) {
        headers["X-Goog-Content-Length-Range"] = `0,${max_size_bytes}`
      }
      $.ajax({
        url: signed_ingress_url,
        type: "PUT",
        data: file,
        contentType: "application/octet-stream",
        headers: headers,
        success: function() {
          // field.val(JSON.stringify({_tmp_path: ingress_path, name: file.name, content_type: file.type}));
          window.gcp_number_of_files--;
          if (window.gcp_number_of_files === 0) {
            window.gcp_uploads_complete = true;
            $(submitEvent.target).submit();
          }
        },
        error: function(result) {
          console.log(result);
          $(".gcp-overlay").css("display", "none");
          window.gcp_uploads_complete = false;
          alert("Error uploading file(s) to Google Cloud. Please refresh and try again.");
        },
        processData: false
      });
    });
  });
});
