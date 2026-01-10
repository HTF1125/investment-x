// ==============================================================================
// GLOBAL CONSTANTS (Configuration)
// ==============================================================================
const API_NAMED_RANGE = "API_URL";

// Chart Defaults
const DEFAULT_CHART_WIDTH = 675;
const DEFAULT_CHART_HEIGHT = 450; 

// ==============================================================================
// CORE CONTEXT HELPERS (Shared across modules)
// ==============================================================================
const App = (() => {
  let apiUrlCache = null;
  const normalizeBase = (base) => String(base || "").replace(/\/$/, "");

  return {
    ss() { return SpreadsheetApp.getActiveSpreadsheet(); },
    ui() { return SpreadsheetApp.getUi(); },
    tz() { return SpreadsheetApp.getActive().getSpreadsheetTimeZone(); },
    getApiUrl() {
      if (apiUrlCache) return apiUrlCache;
      const range = this.ss().getRangeByName(API_NAMED_RANGE);
      if (range) {
        const raw = String(range.getValue()).trim();
        if (raw) {
          apiUrlCache = normalizeBase(raw);
          return apiUrlCache;
        }
      }
      try {
        this.ui().alert(`⚠️ API URL not found. Please set the named range "${API_NAMED_RANGE}".`);
      } catch (e) {}
      return null;
    },
    clearApiUrl() { apiUrlCache = null; },
    buildUrl(base, path) {
      return normalizeBase(base) + "/" + (path.startsWith("/") ? path.substring(1) : path);
    },
    fetchJson(url, options) {
      const response = UrlFetchApp.fetch(url, { ...options, muteHttpExceptions: true });
      const code = response.getResponseCode();
      if (code !== 200 && code !== 201) {
        throw new Error(`Request failed for ${url} returned code ${code}. Server response: ${response.getContentText()}`);
      }
      const text = response.getContentText();
      return text ? JSON.parse(text) : {};
    },
    fetch(url, options) {
      const response = UrlFetchApp.fetch(url, { ...options, muteHttpExceptions: true });
      const code = response.getResponseCode();
      if (code >= 400) {
        throw new Error(`API POST failed with code ${code}: ${response.getContentText()}`);
      }
      return response;
    }
  };
})();

// ==============================================================================
// UI MENU
// ==============================================================================
function onOpen() {
  var ui = SpreadsheetApp.getUi();

  ui.createMenu("🛠️ Tools") // Consolidated Main Menu
    .addSubMenu(
      ui.createMenu("📊 Data & Timeseries")
        .addItem("⬇️ Import Timeseries List", "runImportTimeSeriesList")
        .addItem("⬆️ Push Selected Metadata", "runPushTimeseriesMetadata")
        .addItem("➕ Create New Timeseries", "showNewTimeseriesForm")
        .addSeparator()
        .addItem("🔄 Refresh Custom Data (Selected Table)", "runImportCustomData")
    )
    .addSubMenu(
      ui.createMenu("📂 Files & Uploads")
        .addItem("⬇️ Reload Drive Files", "runImportDriveFiles") 
        .addItem("⬆️ Upload PDF(s) from Computer", "showFileUploadDialog") 
        .addItem("🔗 Upload PDF from URL", "runUploadPdfFromUrl") 
        .addItem("📝 Update Selected Filenames", "runUpdateFilenamesInDrive") 
    )
    .addSubMenu(
      ui.createMenu("🐍 Python")
        .addItem("▶️ Run Python for Selected Cells", "runBatchPythonQueries")
    )
    .addSubMenu(
      ui.createMenu("🧭 Export & Share")
        .addItem("📧 Email Dashboard as Excel", "runEmailDashboardAsExcel")
        .addItem("⬇️ Download Current Sheet as Excel", "downloadNativeExcel")
    )
    .addSubMenu(
      ui.createMenu("🎨 Formatting")
        .addItem("📐 Resize Charts", "resizeActiveCharts")
        .addItem("🔄 Extend Ranges to Full Columns", "extendActiveChartRanges")
    )
    .addToUi();
}

function onInstall() { onOpen(); }

// ==============================================================================
// UI ACTIONS (Wrapper functions with Locking)
// ==============================================================================

/**
 * Executes a function with a document lock and progress toast.
 * @param {string} name - The name of the operation for the toast.
 * @param {function} func - The function to execute.
 */
function withDocumentLock(name, func) {
  var ss = App.ss();
  var ui = App.ui();
  var lock = LockService.getDocumentLock();
  try {
    lock.waitLock(30000); // Wait 30 seconds for the lock
    ss.toast(`Starting: ${name}...`, "Status", 5);
    func();
    ss.toast(`Completed: ${name}`, "Status", 3);
  } catch (e) {
    ui.alert(`❌ Error in ${name}: ${e.message}`);
    console.error(e);
  } finally {
    if (lock.hasLock()) {
        lock.releaseLock();
    }
  }
}

// --- TIMESERIES WRAPPERS (Calls Timeseries.gs services) ---
function runImportTimeSeriesList() {
    withDocumentLock("Import Timeseries List", importTimeSeriesListService);
}

function runPushTimeseriesMetadata() {
    withDocumentLock("Push Timeseries Metadata", pushTimeSeriesMetadataService);
}

function runImportCustomData() {
    withDocumentLock("Refresh Custom Data", importCustomDataService);
}


// --- INSIGHTS WRAPPERS (Calls Insights.gs services) ---
function runImportDriveFiles() {
    withDocumentLock("Reload Drive Files", importDriveFiles);
}

function runUpdateFilenamesInDrive() {
    withDocumentLock("Update Drive Filenames", updateFilenamesInDrive);
}

function runUploadPdfFromUrl() {
    withDocumentLock("Upload PDF from URL", uploadPdfFromUrl);
}

// --- OTHER WRAPPERS (Placeholders) ---
function runPythonQuery() {
    SpreadsheetApp.getUi().alert("Placeholder: Python Query service not implemented.");
}

function runEmailDashboardAsExcel() {
    emailDashboardAsExcel();
}


// ==============================================================================
// UI-SPECIFIC LOGIC (Charts)
// ==============================================================================

function resizeActiveCharts() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheet = ss.getActiveSheet();
  var ui = SpreadsheetApp.getUi();
  var charts = sheet.getCharts();
  
  if (charts.length === 0) { ui.alert("⚠️ No charts found."); return; }

  // Direct resize using defaults - no user input required
  var width = DEFAULT_CHART_WIDTH;
  var height = DEFAULT_CHART_HEIGHT;

  charts.forEach(c => sheet.updateChart(c.modify()
    .setOption('width', width)
    .setOption('height', height)
    .build()));
  ss.toast("Resized " + charts.length + " charts.");
}

function extendActiveChartRanges() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheet = ss.getActiveSheet();
  var ui = SpreadsheetApp.getUi();
  
  if (ui.alert("Extend Chart Ranges", "Convert fixed ranges to full columns for ALL charts?", ui.ButtonSet.YES_NO) !== ui.Button.YES) return;

  var charts = sheet.getCharts();
  charts.forEach(chart => {
    var builder = chart.modify().clearRanges();
    chart.getRanges().forEach(range => {
      // Create a new range from row 1 to max rows using the original columns
      builder.addRange(range.getSheet().getRange(1, range.getColumn(), range.getSheet().getMaxRows(), range.getNumColumns()));
    });
    // Set 1 header row since we are including row 1
    sheet.updateChart(builder.setNumHeaders(1).build()); 
  });
  ss.toast("Updated " + charts.length + " charts.");
}
/**
 * ======================================================================
 * SINGLE FILE EXCEL UPLOADER FOR GOOGLE SHEETS
 * (With Real-Time Progress Bar & Timeout Safety)
 * ======================================================================
 * * INSTRUCTIONS:
 * 1. Go to "Services" (left sidebar) -> Add "Drive API" (v3).
 * 2. Define a Named Range "API_URL" in your sheet containing your endpoint.
 * 3. Save this file and reload your spreadsheet.
 * * ======================================================================
 */

// --- CONFIGURATION ---
const UPLOAD_CHUNK_SIZE = 3000;
const DATE_FORMAT = "yyyy-MM-dd";
const HEADER_ROW_INDEX = 8; // Row where headers are located
const MAX_EXECUTION_TIME_MS = 300 * 1000; // 5 minutes (Stop early to avoid crash)

/**
 * Shows the upload dialog to the user.
 */
function showUploadDialog() {
  const html = HtmlService.createHtmlOutput(DIALOG_HTML_CONTENT)
    .setWidth(450)
    .setHeight(350); 
  SpreadsheetApp.getUi().showModalDialog(html, ' ');
}

/**
 * HELPER: Updates progress in CacheService so the HTML client can read it.
 * Expires in 10 minutes.
 */
function updateProgress(uploadId, message, percent) {
  try {
    const cache = CacheService.getUserCache();
    const status = JSON.stringify({ message: message, percent: percent });
    cache.put("UPLOAD_" + uploadId, status, 600); 
  } catch (e) {
    console.log("Cache error: " + e);
  }
}

/**
 * HELPER: Called by the HTML client every second to check status.
 */
function checkProgress(uploadId) {
  const cache = CacheService.getUserCache();
  const json = cache.get("UPLOAD_" + uploadId);
  return json ? JSON.parse(json) : { message: "Initializing...", percent: 0 };
}

/**
 * MAIN PROCESSING FUNCTION
 * Receives Base64 file data and a unique uploadId from the client.
 */
function processExcelUpload(base64Data, fileName, uploadId) {
  let tempFileId;
  const startTime = new Date().getTime();
  
  try {
    // --- STAGE 1: UPLOAD & CONVERT ---
    updateProgress(uploadId, "Converting Excel file...", 10);
    
    const blob = Utilities.newBlob(Utilities.base64Decode(base64Data), MimeType.MICROSOFT_EXCEL, fileName);
    const resource = { name: "[TEMP] " + fileName, mimeType: MimeType.GOOGLE_SHEETS };
    
    // Requires Drive API v3 enabled in Services
    const tempFile = Drive.Files.create(resource, blob);
    tempFileId = tempFile.id;
    
    // --- STAGE 2: FIND TARGET SHEET ---
    updateProgress(uploadId, "Scanning sheets for data...", 20);
    
    const ss = SpreadsheetApp.openById(tempFileId);
    let allSheets = ss.getSheets();
    let targetSheet = allSheets[0];
    let maxRowsFound = 0;

    // Smart detection: Find the sheet with the most data
    for (let i = 0; i < allSheets.length; i++) {
      let s = allSheets[i];
      let r = s.getLastRow();
      if (r > maxRowsFound) {
        maxRowsFound = r;
        targetSheet = s;
      }
    }
    
    // --- STAGE 3: READ DATA ---
    updateProgress(uploadId, "Reading " + maxRowsFound + " rows...", 30);
    
    const lastRow = targetSheet.getLastRow();
    const lastCol = targetSheet.getLastColumn();
    
    if (lastRow < HEADER_ROW_INDEX + 1) {
      throw new Error("Data too short. Must start after row " + HEADER_ROW_INDEX);
    }

    const totalRowsToGrab = lastRow - HEADER_ROW_INDEX + 1;
    const dataValues = targetSheet.getRange(HEADER_ROW_INDEX, 1, totalRowsToGrab, lastCol).getValues();
    
    // --- STAGE 4: PROCESS & SEND ---
    // Pass startTime and uploadId to handle timeouts/progress inside the loop
    const resultMsg = sendDataFromValues(dataValues, startTime, uploadId);
    
    updateProgress(uploadId, "Done!", 100);
    return resultMsg;

  } catch (e) {
    throw new Error(e.toString());
  } finally {
    // --- STAGE 5: CLEANUP ---
    if (tempFileId) {
      try { DriveApp.getFileById(tempFileId).setTrashed(true); } catch (e) {}
    }
  }
}

/**
 * OPTIMIZED: Builds columnar format data and sends to API in a single request.
 * Format: { dates: [...], columns: { CODE1: [...], CODE2: [...] } }
 * This reduces payload size by 80-90% compared to the old row-by-row format.
 */
function sendDataFromValues(values, startTime, uploadId) {
  let apiUrl = "";
  try {
    apiUrl = SpreadsheetApp.getActiveSpreadsheet().getRangeByName("API_URL").getValue();
  } catch (e) { throw new Error("Named Range 'API_URL' not found."); }

  let cleanBaseUrl = String(apiUrl).trim();
  if (cleanBaseUrl.slice(-1) !== '/') cleanBaseUrl += '/';
  // Use new columnar endpoint
  const endpoint = cleanBaseUrl + "api/upload_data_columnar";

  const numRows = values.length;     
  const numCols = values[0].length;
  const headers = values[0];

  updateProgress(uploadId, "Building columnar data...", 35);

  // Build columnar format in a single pass
  const dates = [];
  const columns = {};
  
  // Initialize column arrays for each code
  for (let c = 1; c < numCols; c++) {
    const code = headers[c];
    if (code != null && code !== "") {
      columns[String(code).trim()] = [];
    }
  }

  // Fill dates and column values
  let validRowCount = 0;
  for (let r = 1; r < numRows; r++) {
    const dateRaw = values[r][0];
    if (!dateRaw) continue;
    
    const formattedDate = formatDateValue(dateRaw);
    if (!formattedDate) continue;
    
    dates.push(formattedDate);
    validRowCount++;
    
    for (let c = 1; c < numCols; c++) {
      const code = headers[c];
      if (code == null || code === "") continue;
      
      const codeKey = String(code).trim();
      const valueRaw = values[r][c];
      
      // Push value or null (preserve column alignment)
      if (typeof valueRaw === 'number' && !isNaN(valueRaw)) {
        columns[codeKey].push(valueRaw);
      } else {
        columns[codeKey].push(null);
      }
    }
    
    // Progress update every 500 rows
    if (r % 500 === 0) {
      const percent = 35 + Math.round((r / numRows) * 30);
      updateProgress(uploadId, `Processing row ${r}/${numRows}...`, percent);
    }
  }

  if (validRowCount === 0) return "No valid data found.";

  // Count non-null values for reporting
  let totalDataPoints = 0;
  for (const code in columns) {
    totalDataPoints += columns[code].filter(v => v !== null).length;
  }

  updateProgress(uploadId, `Uploading ${validRowCount} rows × ${Object.keys(columns).length} columns...`, 70);

  // Send entire dataset in one request (no chunking needed!)
  const payload = { dates: dates, columns: columns };
  const options = {
    'method': 'post',
    'contentType': 'application/json',
    'payload': JSON.stringify(payload),
    'muteHttpExceptions': true
  };

  const response = UrlFetchApp.fetch(endpoint, options);
  const responseCode = response.getResponseCode();
  
  if (responseCode !== 200) {
    const errorText = response.getContentText();
    throw new Error(`API returned ${responseCode}: ${errorText}`);
  }

  updateProgress(uploadId, "Processing complete!", 95);
  
  return `✅ Success! Uploaded ${validRowCount} rows × ${Object.keys(columns).length} columns (${totalDataPoints} data points).`;
}

function formatDateValue(dateInput) {
  if (Object.prototype.toString.call(dateInput) === '[object Date]') {
    return Utilities.formatDate(dateInput, Session.getScriptTimeZone(), DATE_FORMAT);
  }
  if (typeof dateInput === 'string') {
    let d = new Date(dateInput);
    if (!isNaN(d.getTime())) return Utilities.formatDate(d, Session.getScriptTimeZone(), DATE_FORMAT);
  }
  return ""; 
}

// --- EMBEDDED HTML INTERFACE ---
const DIALOG_HTML_CONTENT = `
<!DOCTYPE html>
<html>
  <head>
    <base target="_top">
    <style>
      body { font-family: 'Segoe UI', Roboto, sans-serif; padding: 0; margin: 0; background: #fff; color: #333; }
      .container { padding: 20px; display: flex; flex-direction: column; gap: 15px; }
      h2 { margin: 0 0 10px 0; font-weight: 400; font-size: 22px; }
      
      /* Input & Button */
      input[type="file"] { width: 100%; padding: 5px 0; }
      .btn { 
        background-color: #2e7d32; color: white; padding: 12px; border: none; 
        cursor: pointer; border-radius: 4px; font-size: 16px; width: 100%; 
        transition: 0.2s;
      }
      .btn:hover { background-color: #1b5e20; }
      .btn:disabled { background-color: #a5d6a7; cursor: not-allowed; }

      /* Progress Bar Container */
      .progress-wrapper {
        width: 100%;
        background-color: #e0e0e0;
        border-radius: 4px;
        height: 20px;
        margin-top: 10px;
        display: none; /* Hidden by default */
        overflow: hidden;
      }
      
      /* The Moving Bar */
      .progress-fill {
        height: 100%;
        width: 0%;
        background-color: #4caf50;
        transition: width 0.5s ease;
        text-align: center;
        line-height: 20px;
        color: white;
        font-size: 11px;
        font-weight: bold;
      }

      /* Status Text */
      #status { margin-top: 5px; font-size: 13px; min-height: 20px; word-wrap: break-word;}
      .error-msg { color: #d32f2f; font-weight: bold; }
      .success-msg { color: #2e7d32; font-weight: bold; }
      .info-msg { color: #1976d2; }
    </style>
  </head>
  <body>
    <div class="container">
      <h2>Upload Data</h2>
      
      <div>
        <span style="font-weight:600; font-size:14px;">Select .xlsx file:</span>
        <input type="file" id="fileInput" accept=".xlsx">
      </div>

      <div id="progressWrapper" class="progress-wrapper">
        <div id="progressFill" class="progress-fill">0%</div>
      </div>

      <button id="uploadBtn" class="btn" onclick="uploadFile()">Start Upload</button>
      <div id="status"></div>
    </div>

    <script>
      let pollingInterval;
      
      // Generate a random ID for this upload session
      const uploadId = "ID_" + Math.floor(Math.random() * 1000000);

      function uploadFile() {
        const fileInput = document.getElementById('fileInput');
        const file = fileInput.files[0];
        if (!file) { updateStatus("Please select a file first.", true); return; }

        // Reset UI
        updateStatus("Reading file locally...", false);
        document.getElementById('uploadBtn').disabled = true;
        document.getElementById('progressWrapper').style.display = 'block';
        updateProgressBar(0);

        const reader = new FileReader();
        reader.onload = function(e) {
          const content = e.target.result;
          const base64 = content.split(',')[1];
          
          // Start Polling (Client asks server for updates)
          startPolling();

          // Send to Server
          google.script.run
            .withSuccessHandler(onSuccess)
            .withFailureHandler(onFailure)
            .processExcelUpload(base64, file.name, uploadId);
        };
        reader.readAsDataURL(file);
      }

      function startPolling() {
        // Check progress every 1 second
        pollingInterval = setInterval(function() {
          google.script.run
            .withSuccessHandler(updatePollingUI)
            .checkProgress(uploadId);
        }, 1000);
      }

      function updatePollingUI(data) {
        if (!data) return;
        updateStatus(data.message, false);
        updateProgressBar(data.percent);
      }

      function updateProgressBar(percent) {
        const fill = document.getElementById('progressFill');
        fill.style.width = percent + "%";
        fill.innerText = percent + "%";
      }

      function onSuccess(msg) {
        clearInterval(pollingInterval);
        updateProgressBar(100);
        
        // Check if it was a Partial Success (Timeout warning)
        if(msg.indexOf("PARTIAL") > -1) {
           updateStatus(msg, true); // Show as red/warning
        } else {
           updateStatus(msg, false); // Show as green
        }
        
        document.getElementById('uploadBtn').disabled = false;
        document.getElementById('fileInput').value = '';
      }

      function onFailure(err) {
        clearInterval(pollingInterval);
        updateProgressBar(0);
        updateStatus("Error: " + err.message, true);
        document.getElementById('uploadBtn').disabled = false;
      }

      function updateStatus(msg, isError) {
        const el = document.getElementById('status');
        el.className = isError ? 'error-msg' : 'info-msg';
        el.innerText = msg;
      }
    </script>
  </body>
</html>
`;
const EMAIL_NAMED_RANGE = "Email"; 

function emailDashboardAsExcel() {
  var ss = App.ss();
  var dashboard = ss.getSheetByName("Dashboard");
  
  // 1. Safety Checks
  if (!dashboard) { 
    App.ui().alert("❌ Dashboard sheet not found"); 
    return; 
  }

  var rangeName = (typeof EMAIL_NAMED_RANGE !== 'undefined') ? EMAIL_NAMED_RANGE : "Email";
  var recipientRange = ss.getRangeByName(rangeName);
  
  if (!recipientRange) {
    App.ui().alert("❌ Named Range '" + rangeName + "' not found. Please create it in your sheet.");
    return;
  }
  
  var recipients = recipientRange.getValue();
  if (!recipients) { 
    App.ui().alert("❌ The Email cell is empty."); 
    return; 
  }

  // 2. Create Temp Spreadsheet for Export
  var tempSS = SpreadsheetApp.create("Dashboard_Export_Temp");
  
  // 3. Copy Dashboard & Flatten Formulas (The Fix for #NAME?)
  var tempSheet = dashboard.copyTo(tempSS).setName("Dashboard");
  tempSS.deleteSheet(tempSS.getSheets()[0]); // Delete empty Sheet1
  
  // Get Values from the ORIGINAL dashboard
  var sourceValues = dashboard.getDataRange().getValues();
  
  // Overwrite the Temp sheet with those values (removes formulas)
  tempSheet.getRange(1, 1, sourceValues.length, sourceValues[0].length).setValues(sourceValues);
  
  SpreadsheetApp.flush();
  
  // 4. Export & Email
  try {
    // Generate YYMMDD string
    var today = new Date();
    var formattedDate = Utilities.formatDate(today, Session.getScriptTimeZone(), "yyyyMMdd");
    var fileName = "자산운용Daily_" + formattedDate + ".xlsx";

    var url = "https://docs.google.com/spreadsheets/d/" + tempSS.getId() + "/export?format=xlsx";
    var blob = UrlFetchApp.fetch(url, { 
      headers: { Authorization: "Bearer " + ScriptApp.getOAuthToken() } 
    }).getBlob().setName(fileName); // <--- Updated filename here
    
    MailApp.sendEmail({ 
      to: recipients, 
      subject: "자산운용 Daily (" + formattedDate + ")", // Updated Subject too for clarity
      body: "Please find the Dashboard attached as an Excel file.", 
      attachments: [blob] 
    });
    
    App.ui().alert("✅ Email sent successfully.");
    
  } catch (e) {
    App.ui().alert("❌ Error sending email: " + e.toString());
  } finally {
    // Cleanup
    DriveApp.getFileById(tempSS.getId()).setTrashed(true);
  }
}
// ==============================================================================
// CONFIGURATION
// ==============================================================================
const CONFIG = {
  SHEET_NAME: "Insights",
  FOLDER_ID: "1jkpxtpaZophtkx5Lhvb-TAF9BuKY_pPa", // Replace with your Drive Folder ID
  HEADERS: ["Date", "Issuer", "Name", "Tag", "Type", "Size (MB)", "Last Updated", "URL", "ID"]
};

// ==============================================================================
// MAIN SERVICE: SYNC & TABLE FORMATTING
// ==============================================================================

function importDriveFiles() {
  const ss = App.ss();
  const ui = App.ui();
  let sheet = ss.getSheetByName(CONFIG.SHEET_NAME);
  
  // Create sheet if it doesn't exist
  if (!sheet) {
    sheet = ss.insertSheet(CONFIG.SHEET_NAME);
  }

  // 1. Fetch Data
  let files = [];
  try {
    files = fetchDriveFiles(CONFIG.FOLDER_ID);
  } catch (e) {
    handleError(e);
    return;
  }

  // Sort: Date Descending (Newest first)
  files.sort((a, b) => {
    const dateA = a[0] ? String(a[0]) : "";
    const dateB = b[0] ? String(b[0]) : "";
    return dateB.localeCompare(dateA); 
  });

  if (files.length === 0) {
    console.log("No files found.");
    return;
  }

  // 2. Prepare Sheet (Clear everything to reset formatting)
  sheet.clear(); 

  // 3. Write Headers & Data
  sheet.getRange(1, 1, 1, CONFIG.HEADERS.length).setValues([CONFIG.HEADERS]);
  sheet.getRange(2, 1, files.length, CONFIG.HEADERS.length).setValues(files);

  // 4. APPLY TABLE LOOK (Alternating Colors)
  const range = sheet.getRange(1, 1, files.length + 1, CONFIG.HEADERS.length);
  
  // Remove any previous banding just in case, then apply new
  if (range.getBandings().length > 0) {
    range.getBandings()[0].remove();
  }
  range.applyRowBanding(SpreadsheetApp.BandingTheme.LIGHT_GREY, true, false); // Header=true

  // 5. Header Styling
  sheet.getRange(1, 1, 1, CONFIG.HEADERS.length)
    .setFontWeight('bold')
    .setHorizontalAlignment('center')
    .setVerticalAlignment('middle');
  
  sheet.setFrozenRows(1);

  // 6. TRIM EXTRA COLUMNS (Set sheet columns = table columns)
  const maxCols = sheet.getMaxColumns();
  const requiredCols = CONFIG.HEADERS.length;
  if (maxCols > requiredCols) {
    sheet.deleteColumns(requiredCols + 1, maxCols - requiredCols);
  }

  // 7. Column Widths & Number Formatting
  sheet.autoResizeColumns(1, requiredCols);
  sheet.getRange(2, 1, files.length, 1).setNumberFormat("yyyy-mm-dd"); // Date
  sheet.getRange(2, 6, files.length, 1).setNumberFormat("#,##0.00");   // Size
    
  console.log(`Synced ${files.length} files.`);
}

// ==============================================================================
// SERVICE: UPDATE FILENAMES IN DRIVE (SELECTED ROWS ONLY)
// ==============================================================================

function updateFilenamesInDrive() {
  const ss = App.ss();
  const sheet = ss.getSheetByName(CONFIG.SHEET_NAME);
  const ui = App.ui();
  
  if (!sheet) {
    console.error("Sheet not found");
    return;
  }

  // Get Selected Range
  const selection = sheet.getActiveRange();
  if (!selection) {
    ui.alert("Please select the rows you want to update.");
    return;
  }

  const startRow = selection.getRow();
  const numRows = selection.getNumRows();

  // Validate Selection
  if (startRow + numRows <= 2 && startRow === 1) {
     ui.alert("Please select data rows (starting from row 2).");
     return;
  }

  // Adjust range if header is selected
  let effectiveStartRow = startRow;
  let effectiveNumRows = numRows;

  if (effectiveStartRow < 2) {
    // If selection includes header, offset start to row 2 and decrease count
    const offset = 2 - effectiveStartRow;
    effectiveStartRow = 2;
    effectiveNumRows -= offset;
  }

  if (effectiveNumRows < 1) {
    ui.alert("No valid data rows selected.");
    return;
  }

  // Fetch only the selected rows, but ALL columns to get ID/Date/Issuer/Name
  const dataRange = sheet.getRange(effectiveStartRow, 1, effectiveNumRows, CONFIG.HEADERS.length);
  const data = dataRange.getValues();
  
  let successCount = 0;
  ss.toast(`Processing ${effectiveNumRows} row(s)...`, "Updating", 5);

  try {
    data.forEach(row => {
      const fileId = row[8]; // ID is at index 8 (Column I)
      const dateVal = row[0];
      const issuerVal = row[1];
      const nameVal = row[2];
      const tagVal = row[3];

      if (fileId && nameVal) {
        // Format Date: YYYYMMDD
        let dateStr = "";
        if (dateVal instanceof Date) {
            dateStr = Utilities.formatDate(dateVal, ss.getSpreadsheetTimeZone(), "yyyyMMdd");
        } else {
            // Handle string date "YYYY-MM-DD" -> "YYYYMMDD"
            dateStr = String(dateVal).replace(/-/g, "").substring(0, 8); 
        }

        // Construct new filename: YYYYMMDD_Issuer_Name_Tag.pdf
        const parts = [];
        if (dateStr) parts.push(dateStr);
        if (issuerVal) parts.push(String(issuerVal).trim());
        parts.push(String(nameVal).trim());
        if (tagVal) parts.push(String(tagVal).trim());

        let finalName = parts.join("_");
        if (!finalName.toLowerCase().endsWith(".pdf")) finalName += ".pdf";

        // Rename file in Drive if changed
        try {
          const file = DriveApp.getFileById(fileId);
          if (file.getName() !== finalName) {
            file.setName(finalName);
            successCount++;
          }
        } catch (err) {
          console.warn(`Skipped file ${fileId}: ${err.message}`);
        }
      }
    });
    
    if (successCount > 0) {
      ss.toast(`✅ Updated ${successCount} filename(s) in Drive.`, "Success");
      // Optional: Refresh sheet data to reflect changes
      // importDriveFiles(); 
    } else {
      ss.toast("No filenames required updates in selection.", "Info");
    }

  } catch (e) {
    handleError(e);
  }
}

// ==============================================================================
// HELPER: DRIVE FETCHING
// ==============================================================================

function fetchDriveFiles(folderId) {
  const files = [];
  let pageToken = null;
  const query = `'${folderId}' in parents and trashed = false`;

  do {
    const response = Drive.Files.list({
      q: query,
      pageSize: 1000, 
      pageToken: pageToken,
      fields: "nextPageToken, files(id, name, mimeType, size, modifiedTime, webViewLink)" 
    });
    
    if (response.files) {
      response.files.forEach(f => files.push(parseApiFile(f)));
    }
    pageToken = response.nextPageToken;
  } while (pageToken);
  
  return files;
}

function parseApiFile(item) {
  // Logic: YYYYMMDD_Issuer_Name_Tag.pdf
  const baseName = item.name.replace(/\.[^/.]+$/, ""); // Remove extension
  const parts = baseName.split("_");
  
  let datePart = "", issuerPart = "", namePart = "", tagPart = "";

  if (parts.length >= 4) {
    // Assumption: YYYYMMDD_Issuer_Name(s)_Tag
    datePart = parts[0];
    issuerPart = parts[1];
    tagPart = parts[parts.length - 1]; // Tag is the last part
    namePart = parts.slice(2, parts.length - 1).join(" "); 
  } else if (parts.length === 3) {
    // YYYYMMDD_Issuer_Name (No Tag)
    datePart = parts[0];
    issuerPart = parts[1];
    namePart = parts[2];
  } else if (parts.length === 2 && /^\d{8}$/.test(parts[0])) {
      datePart = parts[0];
      namePart = parts[1];
  } else if (parts.length === 2) {
      issuerPart = parts[0];
      namePart = parts[1];
  } else {
    namePart = baseName;
  }

  if (!datePart) {
    datePart = Utilities.formatDate(new Date(), SpreadsheetApp.getActive().getSpreadsheetTimeZone(), "yyyyMMdd");
  }
  const formattedDate = datePart.length === 8 
    ? `${datePart.substring(0,4)}-${datePart.substring(4,6)}-${datePart.substring(6,8)}`
    : datePart;

  return [
    formattedDate, 
    issuerPart, 
    namePart, 
    tagPart, // New Column
    item.mimeType === "application/pdf" ? "PDF" : "File", 
    Number((parseInt(item.size||0) / 1024 / 1024).toFixed(2)), 
    Utilities.formatDate(new Date(item.modifiedTime), SpreadsheetApp.getActive().getSpreadsheetTimeZone(), "yyyy-MM-dd HH:mm"), 
    item.webViewLink, 
    item.id 
  ];
}

function handleError(e) {
  let msg = e.toString();
  if (msg.includes("Drive is not defined")) {
    msg = "⚠️ ADVANCED DRIVE SERVICE NOT ENABLED.\n\nGo to Editor > Services (+) > Add 'Drive API'.";
  }
  console.error("Error: " + msg);
  try {
     SpreadsheetApp.getUi().alert("❌ Error: " + msg);
  } catch(e) {
     // UI not available
  }
}

// ==============================================================================
// UPLOAD HELPERS
// ==============================================================================

function showFileUploadDialog() {
  const html = HtmlService.createHtmlOutput(getUploadHtml()).setWidth(400).setHeight(350);
  App.ui().showModalDialog(html, 'Upload Files');
}

function uploadPdfFromUrl() {
  const ui = App.ui();
  const result = ui.prompt('Upload File from URL', 'Paste PDF URL:', ui.ButtonSet.OK_CANCEL);

  if (result.getSelectedButton() == ui.Button.OK) {
    const url = result.getResponseText().trim();
    if (!url) return;
    try {
      const response = UrlFetchApp.fetch(url);
      const blob = response.getBlob();
      let filename = url.split('/').pop().split('?')[0] || "DL_" + new Date().getTime() + ".pdf";
      blob.setName(filename);
      DriveApp.getFolderById(CONFIG.FOLDER_ID).createFile(blob);
      importDriveFiles(); 
      ui.alert("✅ File added.");
    } catch (e) {
      ui.alert("❌ Error: " + e.toString());
    }
  }
}

function processFileUpload(data) {
  try {
    const folder = DriveApp.getFolderById(CONFIG.FOLDER_ID);
    const blob = Utilities.newBlob(Utilities.base64Decode(data.fileData), data.mimeType, data.fileName);
    folder.createFile(blob);
    importDriveFiles(); 
    return { status: "success", message: "✅ Saved: " + data.fileName };
  } catch (error) {
    return { status: "error", message: "❌ Error: " + error.toString() };
  }
}

function getUploadHtml() {
  return `<!DOCTYPE html>
    <html>
      <head>
        <base target="_top">
        <style>
          body { font-family: 'Segoe UI', sans-serif; padding: 20px; text-align: center; color: #333; }
          .drop-zone { width: 90%; margin: 0 auto; height: 140px; border: 2px dashed #4A90E2; border-radius: 8px; background-color: #f8fbff; position: relative; display: flex; flex-direction: column; align-items: center; justify-content: center; transition: all 0.3s; }
          .drop-zone:hover { background-color: #eef5fc; border-color: #2c66aa; }
          .drop-zone input[type="file"] { position: absolute; width: 100%; height: 100%; top: 0; left: 0; opacity: 0; cursor: pointer; }
          .icon { font-size: 32px; margin-bottom: 8px; }
          .bold { font-weight: 600; color: #4A90E2; }
          .hint { font-size: 12px; color: #888; margin-top: 5px; }
          .btn { margin-top: 20px; background-color: #4A90E2; color: white; border: none; padding: 10px 25px; border-radius: 4px; cursor: pointer; font-weight: 600; width: 90%; display: none; }
          .btn:disabled { background-color: #ccc; cursor: not-allowed; }
          #status { margin-top: 15px; font-size: 13px; min-height: 20px; }
          .success { color: green; font-weight: bold; }
          .error { color: red; }
        </style>
        <script>
          function handleFileSelect(input) {
            var files = input.files;
            if (files.length > 0) {
               var text = files.length === 1 ? files[0].name : files.length + " files selected";
               document.getElementById('desc').innerHTML = "📄 " + text;
               document.getElementById('submitBtn').style.display = 'inline-block';
            }
          }
          function handleFormSubmit(formObject) {
            var btn = document.getElementById('submitBtn');
            var status = document.getElementById('status');
            btn.value = 'Uploading...'; btn.disabled = true; status.innerHTML = '⏳ Uploading...';
            
            var file = formObject.myFile.files[0];
            var reader = new FileReader();
            reader.onload = function(e) {
              var base64Data = e.target.result.split(",")[1];
              google.script.run
                .withSuccessHandler(function(res) {
                   if(res.status === "success") {
                      status.className = "success"; status.innerHTML = res.message;
                      document.getElementById('myForm').reset();
                      document.getElementById('desc').innerHTML = '<span class="icon">📂</span><span class="bold">Drop files here</span>';
                      btn.style.display = 'none'; btn.disabled = false; btn.value = 'Upload Now';
                   } else {
                      status.className = "error"; status.innerHTML = res.message;
                      btn.disabled = false; btn.value = 'Try Again';
                   }
                })
                .processFileUpload({ fileName: file.name, mimeType: file.type, fileData: base64Data });
            };
            reader.readAsDataURL(file);
          }
        </script>
      </head>
      <body>
        <form id="myForm" onsubmit="handleFormSubmit(this); return false;">
          <div class="drop-zone">
              <input type="file" name="myFile" accept=".pdf" required onchange="handleFileSelect(this)">
              <div id="desc"><span class="icon">📂</span><span class="bold">Drop files here</span><div class="hint">or Click to Browse</div></div>
          </div>
          <input type="submit" value="Upload Now" id="submitBtn" class="btn">
          <div id="status"></div>
        </form>
      </body>
    </html>`;
}
/**
 * Run this function.
 * v6.2: FORCE TEXT PRESERVATION.
 * Detects strings with leading zeros ("033") and forces the destination
 * cell to Plain Text (@) so Excel does not convert it to a number.
 */
function downloadNativeExcel() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sourceSheet = ss.getActiveSheet();
  var sheetName = sourceSheet.getName();

  ss.toast('Reading data...', 'Step 1/3', 60);

  var tempSSId = null;

  try {
    // --- STEP 1: READ DATA INTO MEMORY ---
    var sourceRange = sourceSheet.getDataRange();
    var values = sourceRange.getValues();
    var numberFormats = sourceRange.getNumberFormats();
    
    var numRows = values.length;
    var numCols = values[0].length;
    
    // --- STEP 1.5: THE FIX FOR "033" ---
    // Perform light check for leading zero strings
    for (var r = 0; r < numRows; r++) {
      for (var c = 0; c < numCols; c++) {
        var val = values[r][c];
        if (typeof val === 'string' && val.length > 1 && val.charCodeAt(0) === 48 && /^\d+$/.test(val)) {
           numberFormats[r][c] = "@"; 
        }
      }
    }

    ss.toast('Creating copy...', 'Step 2/3', 60);

    // --- STEP 2: CREATE & COPY (Optimized) ---
    var newSS_File = SpreadsheetApp.create(sheetName);
    tempSSId = newSS_File.getId();
    Utilities.sleep(500); // Minimal wait

    // Use copyTo for fast full-clone (preserving widths/styles)
    var destSheet = sourceSheet.copyTo(newSS_File);
    destSheet.setName(sheetName);
    newSS_File.deleteSheet(newSS_File.getSheets()[0]); // Remove empty Sheet1
    
    // --- STEP 3: FLATTEN & FORMAT ---
    var destRange = destSheet.getRange(1, 1, numRows, numCols);
    
    // Apply formats BEFORE values to ensure "033" stays as text
    destRange.setNumberFormats(numberFormats);
    
    // Write values to flatten formulas
    destRange.setValues(values);

    SpreadsheetApp.flush();
    
    ss.toast('Downloading...', 'Step 3/3', 60);

    // --- STEP 4: DOWNLOAD ---
    var url = "https://docs.google.com/spreadsheets/d/" + tempSSId + "/export?format=xlsx";
    var params = {
      method: "get",
      headers: { "Authorization": "Bearer " + ScriptApp.getOAuthToken() },
      muteHttpExceptions: true
    };
    
    var response = UrlFetchApp.fetch(url, params);
    
    if (response.getResponseCode() !== 200) {
       Utilities.sleep(1000); // Retry once
       response = UrlFetchApp.fetch(url, params);
       if (response.getResponseCode() !== 200) {
         throw new Error("Download failed code: " + response.getResponseCode());
       }
    }
    
    var blob = response.getBlob();
    var b64 = Utilities.base64Encode(blob.getBytes());
    var filename = sheetName + "_" + Utilities.formatDate(new Date(), Session.getScriptTimeZone(), "yyyy-MM-dd") + ".xlsx";

    // --- STEP 5: GUI ---
    var htmlString = `
      <html>
        <style>
          body { font-family: sans-serif; text-align: center; padding-top: 25px; background-color: #f4f4f4; }
          .btn { background-color: #4CAF50; color: white; padding: 12px 25px; text-decoration: none; border-radius: 4px; }
        </style>
        <body>
          <p>Ready!</p>
          <a id="dl" href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,${b64}" download="${filename}" class="btn">Save File</a>
          <script>
            setTimeout(function() { document.getElementById('dl').click(); }, 500);
            setTimeout(function() { google.script.host.close(); }, 6000);
          </script>
        </body>
      </html>
    `;
    
    SpreadsheetApp.getUi().showModalDialog(HtmlService.createHtmlOutput(htmlString).setWidth(300).setHeight(150), 'Download');

  } catch (e) {
    SpreadsheetApp.getUi().alert("Error: " + e.toString());
  } finally {
    if (tempSSId) { try { DriveApp.getFileById(tempSSId).setTrashed(true); } catch(e) {} }
  }
}
/**
 * loops through all currently selected cells (active range list),
 * reads the Python code, and executes the query for each one.
 * Shows a progress bar dialog instead of multiple toasts.
 */
function runBatchPythonQueries() {
  const ss = App.ss();
  const ui = App.ui();
  const sheet = ss.getActiveSheet();
  
  // Get all selected ranges (supports non-contiguous selections via Ctrl+Click)
  const rangeList = sheet.getActiveRangeList();
  
  if (!rangeList) {
    ui.alert("⚠️ Please select at least one cell.");
    return;
  }

  const ranges = rangeList.getRanges();
  const baseApiUrl = getApiUrl(ss); // Assumes this global function exists
  if (!baseApiUrl) return;

  // 1. PRE-READ STEP: 
  const executionQueue = [];

  ranges.forEach(range => {
    const numRows = range.getNumRows();
    const numCols = range.getNumColumns();
    const startRow = range.getRow();
    const startCol = range.getColumn();

    // OPTIMIZATION: Fetch all values into memory at once.
    // Iterating through a JS array is instant; calling .getValue() 
    // on every cell individually is very slow.
    const values = range.getValues();

    for (let r = 0; r < numRows; r++) {
      for (let c = 0; c < numCols; c++) {
        const code = values[r][c];
        
        // Only get the specific Range object if we actually found code.
        // This fast-skips empty cells without hitting the Spreadsheet API.
        if (code && typeof code === 'string' && code.trim() !== "") {
          executionQueue.push({
            cell: sheet.getRange(startRow + r, startCol + c),
            code: code
          });
        }
      }
    }
  });

  if (executionQueue.length === 0) {
    ui.alert("⚠️ No valid code found in selection.");
    return;
  }

  // 2. SETUP PROGRESS UI
  // We use CacheService to communicate progress to the HTML dialog
  const cache = CacheService.getUserCache();
  const progressKey = 'BATCH_QUERY_PROGRESS';
  const total = executionQueue.length;
  let successCount = 0;
  let errorCount = 0;

  // Initialize progress state
  cache.put(progressKey, JSON.stringify({ 
    processed: 0, 
    total: total, 
    errors: 0, 
    complete: false 
  }));

  // Render the Progress Bar Dialog
  const htmlOutput = HtmlService.createHtmlOutput(getProgressBarHtml(total))
      .setWidth(400)
      .setHeight(160);
  ui.showModelessDialog(htmlOutput, 'Executing Python Queries...');

  // 3. EXECUTION STEP
  executionQueue.forEach((item, index) => {
    try {
      // Update Progress Cache for the Dialog to read
      cache.put(progressKey, JSON.stringify({ 
        processed: index + 1, // We are currently processing or just finished this index
        total: total, 
        errors: errorCount,
        complete: false
      }));

      // Call the helper function for the individual cell
      executePythonForCell(ss, sheet, item.cell, item.code, baseApiUrl);
      successCount++;
      
      // Optional: Short sleep to prevent hitting API rate limits if applicable
      Utilities.sleep(200); 

    } catch (e) {
      console.error(`Error at ${item.cell.getA1Notation()}: ${e.toString()}`);
      errorCount++;
      item.cell.setBackground('#f4cccc'); 
    }
  });

  // Signal completion to the dialog (so it can close itself)
  cache.put(progressKey, JSON.stringify({ 
    processed: total, 
    total: total, 
    errors: errorCount, 
    complete: true 
  }));
  
  // Final summary toast
  ss.toast(`Completed. Success: ${successCount}, Errors: ${errorCount}`, "Batch Finished", 5);
}

/**
 * Helper: Generates the HTML for the progress bar dialog.
 * This includes client-side JS to poll the server for progress updates.
 */
function getProgressBarHtml(totalCount) {
  return `
    <!DOCTYPE html>
    <html>
      <head>
        <style>
          body { font-family: 'Google Sans', sans-serif; padding: 10px; text-align: center; }
          .progress-container { width: 100%; background-color: #f1f3f4; border-radius: 4px; height: 20px; margin: 15px 0; overflow: hidden; }
          .progress-bar { width: 0%; height: 100%; background-color: #1a73e8; transition: width 0.5s ease; }
          .status-text { font-size: 14px; color: #202124; margin-bottom: 5px; }
          .error-text { font-size: 12px; color: #d93025; margin-top: 5px; height: 15px;}
        </style>
      </head>
      <body>
        <div class="status-text" id="status">Starting batch execution...</div>
        <div class="progress-container">
          <div class="progress-bar" id="bar"></div>
        </div>
        <div class="status-text" id="counter">0 / ${totalCount}</div>
        <div class="error-text" id="errors"></div>

        <script>
          // Poll the server every 800ms to check progress
          const intervalId = setInterval(checkProgress, 800);

          function checkProgress() {
            google.script.run.withSuccessHandler(updateUi).getBatchProgress();
          }

          function updateUi(dataJson) {
            if (!dataJson) return; // No data yet
            const data = JSON.parse(dataJson);

            // Update Text
            document.getElementById('counter').textContent = data.processed + ' / ' + data.total;
            document.getElementById('status').textContent = data.complete ? 'Finished!' : 'Processing...';
            
            // Update Bar Width
            const pct = Math.round((data.processed / data.total) * 100);
            document.getElementById('bar').style.width = pct + '%';
            
            // Show errors if any
            if (data.errors > 0) {
              document.getElementById('errors').textContent = data.errors + ' errors encountered';
            }

            // Close dialog if complete
            if (data.complete) {
              clearInterval(intervalId);
              setTimeout(() => google.script.host.close(), 1500); // Close after 1.5s delay
            }
          }
        </script>
      </body>
    </html>
  `;
}

/**
 * Public function called by the client-side HTML to get current status.
 */
function getBatchProgress() {
  return CacheService.getUserCache().get('BATCH_QUERY_PROGRESS');
}

/**
 * Helper function containing the specific logic to run a query for a single cell.
 * Extracted from the original runPythonQueryInPlaceService.
 */
function executePythonForCell(ss, sheet, activeCell, code, baseApiUrl) {
  // 1. Prepare Payload
  const payload = { "code": code, "format": "json" };

  // 2. Call API
  // Assumes fetchJsonWithRetry and buildApiUrl exist globally per original snippet
  const responseData = fetchJsonWithRetry(buildApiUrl(baseApiUrl, "api/data/evaluation"), {
    method: "post",
    contentType: "application/json",
    payload: JSON.stringify(payload)
  });

  // 3. Parse Data (Column-Store -> Row-Store)
  const columns = Object.keys(responseData);
  if (columns.length === 0) {
    return; // Empty result, do nothing
  }

  const rowCount = responseData[columns[0]].length;
  
  // Build the 2D array (Headers + Data)
  const outputTable = [columns]; 

  for (let i = 0; i < rowCount; i++) {
    const row = [];
    for (let j = 0; j < columns.length; j++) {
      const colName = columns[j];
      let val = responseData[colName][i];

      if (typeof val === 'string') {
        // Simple regex check for dates to convert them to native Sheet Date objects
        if (/^\d{4}-\d{2}-\d{2}/.test(val)) {
            const d = new Date(val);
            if (!isNaN(d.getTime())) val = d;
        }
      }
      row.push(val === null ? "" : val);
    }
    outputTable.push(row);
  }

  // 4. Write Result Below Active Cell
  const startRow = activeCell.getRow() + 1;
  const startCol = activeCell.getColumn();
  const numRows = outputTable.length;
  const numCols = outputTable[0].length;

  // Extend sheet if necessary
  if (startRow + numRows > sheet.getMaxRows()) {
    sheet.insertRowsAfter(sheet.getMaxRows(), (startRow + numRows) - sheet.getMaxRows());
  }

  // Clear previous results
  // WARNING: This clears strictly below the cell. If processing batch in one column,
  // ensure sufficient spacing or this will clear subsequent results.
  const rowsToClear = sheet.getMaxRows() - startRow + 1;
  if (rowsToClear > 0) {
    // Only clear the specific columns used by the data to minimize collateral damage
    sheet.getRange(startRow, startCol, rowsToClear, numCols).clearContent();
  }

  // Write new data
  const targetRange = sheet.getRange(startRow, startCol, numRows, numCols);
  targetRange.setValues(outputTable);

  if (numRows > 1) {
    sheet.getRange(startRow + 1, startCol, numRows - 1, 1).setNumberFormat("yyyy-MM-dd");
    if (numCols > 1) {
      sheet.getRange(startRow + 1, startCol + 1, numRows - 1, numCols - 1).setNumberFormat("#,##0.00");
    }
  }

  // Formatting
  const headerRange = sheet.getRange(startRow, startCol, 1, numCols);
  headerRange.setFontWeight("bold").setBorder(false, false, true, false, false, false);
}
// ==============================================================================
// CONFIGURATION
// ==============================================================================
// const TIMESERIES_SHEET_NAME = "Timeseries"; // Defined in Code.gs
const BATCH_SIZE = 2000; 
const TIMESERIES_SHEET_NAME = "Timeseries"; 

// NOTE: All utility functions (getApiUrl, fetchJsonWithRetry, toDateStr, etc.) 
// are assumed to be defined in utils.gs and accessible globally.

// Encapsulated Timeseries logic to keep menu wrappers thin
const TimeseriesService = {
  headers() {
    return [
      "id", "code", "name", "favorite", "frequency", "source",
      "source_code", "country", "currency", "scale", "unit",
      "remark", "asset_class", "provider", "category", "start",
      "end", "num_data"
    ];
  },

  importList() {
    const ss = App.ss();
    const ui = App.ui();
    const baseApiUrl = App.getApiUrl();
    if (!baseApiUrl) return;

    try {
      const data = App.fetchJson(App.buildUrl(baseApiUrl, "api/timeseries"), { method: "get" });
      if (!data || data.length === 0) {
        ui.alert("⚠️ No data returned from API.");
        return;
      }

      const headers = this.headers();
      const tableData = data.map(item => headers.map(h => item[h] ?? ""));
      const sheet = writeTableFast(ss, TIMESERIES_SHEET_NAME, headers, tableData);

      const favIndex = headers.indexOf("favorite") + 1;
      if (favIndex > 0 && tableData.length > 0) {
        sheet.getRange(2, favIndex, tableData.length, 1).insertCheckboxes();
      }

      const requiredRows = tableData.length + 1;
      const requiredCols = headers.length;
      const currentRows = sheet.getMaxRows();
      const currentCols = sheet.getMaxColumns();

      if (currentRows > requiredRows) {
        sheet.deleteRows(requiredRows + 1, currentRows - requiredRows);
      }
      if (currentCols > requiredCols) {
        sheet.deleteColumns(requiredCols + 1, currentCols - requiredCols);
      }

      ui.alert(`✅ Imported ${tableData.length} records and resized sheet.`);
    } catch (e) {
      console.error(e);
      ui.alert(`❌ Error: ${e.toString()}`);
    }
  },

  pushSelected() {
    const ss = App.ss();
    const ui = App.ui();
    const sheet = ss.getActiveSheet();

    if (sheet.getName() !== TIMESERIES_SHEET_NAME) {
      ui.alert(`❌ Wrong Sheet. Please select rows in the '${TIMESERIES_SHEET_NAME}' sheet.`);
      return;
    }

    const baseApiUrl = App.getApiUrl();
    if (!baseApiUrl) return;

    const lastCol = sheet.getLastColumn();
    const headerValues = sheet.getRange(1, 1, 1, lastCol).getValues()[0];
    const idColIndex = headerValues.indexOf("id");
    const codeColIndex = headerValues.indexOf("code");

    if (codeColIndex === -1) {
      ui.alert("❌ Required header (code) not found.");
      return;
    }

    const activeRange = sheet.getActiveRange();
    if (!activeRange) {
      ui.alert("⚠️ No rows selected.");
      return;
    }

    const startRow = activeRange.getRow();
    const numRows = activeRange.getNumRows();

    if (startRow === 1 && numRows === 1) {
      ui.alert("⚠️ You selected only the header row.");
      return;
    }

    const rows = sheet.getRange(startRow, 1, numRows, lastCol).getValues();
    const recordsToPush = [];
    const rowIndices = [];

    for (let i = 0; i < rows.length; i++) {
      if (startRow + i === 1) continue;
      const row = rows[i];
      const recordCode = row[codeColIndex];
      if (recordCode && recordCode !== "") {
        const obj = {};
        for (let c = 0; c < headerValues.length; c++) {
          const h = headerValues[c];
          if (!h || h === "id") continue;
          const v = row[c];
          if (v !== "" && v != null) {
            obj[h] = Object.prototype.toString.call(v) === "[object Date]" ? toDateStr(v) : v;
          }
        }
        obj.code = obj.code || recordCode;
        recordsToPush.push(obj);
        rowIndices.push(startRow + i);
      }
    }

    if (recordsToPush.length === 0) {
      ui.alert("⚠️ No valid records (with code) found in your selection.");
      return;
    }

    if (recordsToPush.length === 1) {
      const record = recordsToPush[0];
      const code = record.code;
      const url = App.buildUrl(baseApiUrl, `api/timeseries/${encodeURIComponent(code)}`);
      try {
        let response;
        try {
          response = App.fetchJson(url, {
            method: "put",
            contentType: "application/json",
            payload: JSON.stringify(record)
          });
        } catch (err) {
          if (String(err).includes("code 404")) {
            response = App.fetchJson(url, {
              method: "post",
              contentType: "application/json",
              payload: JSON.stringify(record)
            });
          } else {
            throw err;
          }
        }

        if (response && response.id && idColIndex >= 0) {
          sheet.getRange(rowIndices[0], idColIndex + 1).setValue(response.id);
        }
        ui.alert(`✅ Synced record: ${code}`);
      } catch (e) {
        ui.alert(`❌ Update Failed: ${e.toString()}`);
      }
      return;
    }

    let successCount = 0;
    let payloadBatch = [];
    for (let i = 0; i < recordsToPush.length; i++) {
      payloadBatch.push(recordsToPush[i]);
      const isLast = i === recordsToPush.length - 1;
      if (payloadBatch.length >= BATCH_SIZE || isLast) {
        try {
          const response = App.fetchJson(App.buildUrl(baseApiUrl, "api/timeseries"), {
            method: "post",
            contentType: "application/json",
            payload: JSON.stringify(payloadBatch)
          });
          if (response.error_count && response.error_count > 0) {
            throw new Error(`API reported errors: ${response.errors.join("; ")}`);
          }
          successCount += payloadBatch.length;
          payloadBatch = [];
        } catch (e) {
          ui.alert(`❌ Update Failed (After ${successCount} successful): ${e.toString()}`);
          return;
        }
      }
    }
    ui.alert(`✅ Successfully updated ${successCount} selected records.`);
  },

  importCustomData() {
    const ss = App.ss();
    const ui = App.ui();
    const sheet = ss.getActiveSheet();
    const activeCell = sheet.getActiveCell();

    if (!activeCell) { ui.alert("⚠️ Select the 'Date' header cell."); return; }

    const startRow = activeCell.getRow();
    const startCol = activeCell.getColumn();
    const maxPotentialCols = sheet.getLastColumn() - startCol + 1;
    if (maxPotentialCols < 1) return;

    const rawRow = sheet.getRange(startRow, startCol, 1, maxPotentialCols).getValues()[0];
    const codes = [];
    for (let val of rawRow) {
      if (val === "" || val == null) break;
      codes.push(String(val).replace(/[\r\n]+/g, " ").trim());
    }

    if (codes.length < 2) {
      ui.alert("❌ No codes found to the right of Date.");
      return;
    }

    const baseApiUrl = App.getApiUrl();
    if (!baseApiUrl) return;

    let url = App.buildUrl(baseApiUrl, "api/timeseries.custom");
    const startRange = ss.getRangeByName("StartDate");
    if (startRange) {
      const sDate = startRange.getValue();
      if (sDate instanceof Date) {
        url += "?start_date=" + Utilities.formatDate(sDate, ss.getSpreadsheetTimeZone(), "yyyy-MM-dd");
      }
    }

    let json;
    try {
      json = App.fetchJson(url, { method: "get", headers: { "X-Codes": JSON.stringify(codes) } });
    } catch (e) {
      ui.alert("❌ API Error: " + e.toString());
      return;
    }

    const apiCols = Object.keys(json);
    if (apiCols.length === 0) { ui.alert("⚠ No data returned."); return; }
    const apiColSet = new Set(apiCols);
    if (!apiColSet.has("Date")) { ui.alert("⚠ Data returned but missing 'Date' column."); return; }

    const rowCount = json["Date"].length;
    const table = new Array(rowCount);
    for (let r = 0; r < rowCount; r++) {
      const row = new Array(codes.length);
      for (let c = 0; c < codes.length; c++) {
        const h = codes[c];
        if (!apiColSet.has(h)) { row[c] = ""; continue; }
        const v = json[h][r];
        row[c] = (v && h === "Date") ? new Date(v) : v;
      }
      table[r] = row;
    }

    const maxRows = sheet.getMaxRows();
    if (maxRows > startRow) {
      sheet.getRange(startRow + 1, startCol, maxRows - startRow, codes.length).clearContent();
    }
    if (table.length > 0) {
      sheet.getRange(startRow + 1, startCol, table.length, codes.length).setValues(table);
      ui.alert(`✅ Updated ${table.length} rows.`);
    }
  },

  showCreateForm() {
    const html = HtmlService.createHtmlOutput(this.getCreateFormHtml())
      .setWidth(500)
      .setHeight(600);
    App.ui().showModalDialog(html, "➕ Create New Timeseries Record");
  },

  processCreateForm(formObject) {
    const ss = App.ss();
    const sheet = ss.getSheetByName(TIMESERIES_SHEET_NAME);
    if (!sheet) {
      return "❌ Error: Sheet '" + TIMESERIES_SHEET_NAME + "' not found. Cannot insert data.";
    }

    const baseApiUrl = App.getApiUrl();
    if (!baseApiUrl) {
      return "❌ Error: API URL not configured.";
    }

    const headers = sheet.getRange(1, 1, 1, sheet.getLastColumn()).getValues()[0];
    const newCode = String(formObject.code || "").trim().toUpperCase();
    if (!newCode) {
      return "❌ Error: Code field is required.";
    }

    const payload = {};
    for (let i = 0; i < headers.length; i++) {
      const header = headers[i];
      const formValue = formObject[header];
      if (formValue != null && formValue !== "") {
        if (header === "favorite") {
          payload[header] = (formValue === "on");
        } else {
          payload[header] = formValue;
        }
      }
    }
    payload["code"] = newCode;

    try {
      const createUrl = App.buildUrl(baseApiUrl, `api/timeseries/${encodeURIComponent(newCode)}`);
      const response = App.fetchJson(createUrl, {
        method: "post",
        contentType: "application/json",
        payload: JSON.stringify(payload)
      });

      if (!response || !response.id) {
        throw new Error(`Record created, but API did not return complete metadata for code: ${newCode}`);
      }

      const newRow = new Array(headers.length).fill("");
      for (let i = 0; i < headers.length; i++) {
        const h = headers[i];
        const v = response[h];
        if (v != null) {
          newRow[i] = v;
        }
      }

      const lastRow = sheet.getLastRow();
      const targetRange = sheet.getRange(lastRow + 1, 1, 1, newRow.length);
      targetRange.setValues([newRow]);

      const favIndex = headers.indexOf("favorite");
      if (favIndex >= 0) {
        const range = sheet.getRange(lastRow + 1, favIndex + 1);
        range.insertCheckboxes().setValue(response.favorite === true);
      }

      return `✅ Record **${response.code}** successfully created in API and inserted into sheet at row ${lastRow + 1}.`;
    } catch (e) {
      return "❌ API/Sheet Insertion Error: " + e.toString();
    }
  },

  getCreateFormHtml() {
    return `
    <!DOCTYPE html>
    <html>
      <head>
        <base target="_top">
        <style>
          body { font-family: Arial, sans-serif; padding: 15px; background-color: #f4f4f4; }
          form { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
          label { display: block; margin-bottom: 5px; font-weight: bold; color: #333; }
          input[type="text"], input[type="number"], select, textarea {
            width: 100%;
            padding: 8px;
            margin-bottom: 15px;
            border: 1px solid #ccc;
            border-radius: 4px;
            box-sizing: border-box;
          }
          .half { width: calc(50% - 10px); display: inline-block; }
          .half:first-child { margin-right: 20px; }
          .checkbox-container { margin-bottom: 15px; }
          button {
            background-color: #4A90E2;
            color: white;
            padding: 10px 15px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 16px;
          }
          button:hover { background-color: #3a70b6; }
          #status { margin-top: 15px; font-weight: bold; }
          .required-field { color: red; }
        </style>
        <script>
          function handleFormSubmit(formObject) {
            const btn = document.getElementById('submitBtn');
            const status = document.getElementById('status');
            btn.disabled = true;
            btn.textContent = 'Syncing...';
            status.innerHTML = '<span style="color: blue;">⏳ Creating record in API...</span>';
            google.script.run
              .withSuccessHandler(onSuccess)
              .withFailureHandler(onFail)
              .processNewTimeseriesForm(formObject);
          }
          function onSuccess(msg) {
            const btn = document.getElementById('submitBtn');
            const status = document.getElementById('status');
            status.innerHTML = msg.includes('Error') ? 
                             '<span style="color: red;">' + msg + '</span>' :
                             '<span style="color: green;">' + msg + '</span>';
            btn.disabled = false;
            btn.textContent = 'Create Record';
            if (!msg.includes('Error')) {
                document.getElementById('myForm').reset(); 
            }
          }
          function onFail(error) {
            const btn = document.getElementById('submitBtn');
            const status = document.getElementById('status');
            status.innerHTML = '<span style="color: red;">❌ Server Error: ' + error.message + '</span>';
            btn.disabled = false;
            btn.textContent = 'Create Record';
          }
        </script>
      </head>
      <body>
        <form id="myForm" onsubmit="handleFormSubmit(this); return false;">
          <label for="code"><span class="required-field">*</span> Code (Ticker/Identifier):</label>
          <input type="text" id="code" name="code" required maxlength="50">
          <label for="name">Name / Description:</label>
          <input type="text" id="name" name="name" maxlength="200">
          <div class="half">
            <label for="provider">Provider:</label>
            <input type="text" id="provider" name="provider" maxlength="100">
          </div>
          <div class="half">
            <label for="asset_class">Asset Class:</label>
            <input type="text" id="asset_class" name="asset_class" maxlength="50">
          </div>
          <label for="category">Category:</label>
          <input type="text" id="category" name="category" maxlength="100">
          <div class="half">
            <label for="source">Source:</label>
            <input type="text" id="source" name="source" maxlength="100">
          </div>
          <div class="half">
            <label for="source_code">Source Code (External ID):</label>
            <input type="text" id="source_code" name="source_code" maxlength="2000">
          </div>
          <div class="half">
            <label for="frequency">Frequency (e.g., D, W, M):</label>
            <input type="text" id="frequency" name="frequency" maxlength="20">
          </div>
          <div class="half">
            <label for="currency">Currency (e.g., USD):</label>
            <input type="text" id="currency" name="currency" maxlength="10">
          </div>
          <label for="scale">Scale (e.g., 1, 1000, 1000000):</label>
          <input type="number" id="scale" name="scale">
          <label for="remark">Remark (Long Description):</label>
          <textarea id="remark" name="remark" rows="3"></textarea>
          <div class="checkbox-container">
            <label>
                <input type="checkbox" id="favorite" name="favorite"> Favorite (Check to enable fast access/loading)
            </label>
          </div>
          <button type="submit" id="submitBtn">Create Record</button>
          <div id="status"></div>
        </form>
      </body>
    </html>`;
  }
};

// ==============================================================================
// SERVICE: TIMESERIES IMPORT (LIST ALL)
// ==============================================================================
/**
 * Fetches all Time Series data from the API and writes it to the designated sheet.
 * Resizes the sheet (deletes empty rows/cols) to fit the data exactly.
 * Corresponds to: GET /api/timeseries
 */
function importTimeSeriesListService() {
  return TimeseriesService.importList();
}

// ==============================================================================
// SERVICE: PUSH SELECTED TIMESERIES (Update Only)
// ==============================================================================
/**
 * Pushes ONLY the rows currently selected by the user cursor/mouse.
 * For single row: uses PUT /api/timeseries/{code}
 * For multiple rows: uses bulk POST /api/timeseries
 * Updates id field in sheet from API response.
 */
function pushTimeSeriesMetadataService() {
  return TimeseriesService.pushSelected();
}

// ==============================================================================
// SERVICE: CUSTOM DATA IMPORT
// ==============================================================================
/**
 * Fetches time series data for codes specified on the current sheet.
 */
function importCustomDataService() {
  return TimeseriesService.importCustomData();
}

// ==============================================================================
// UI: TIMESERIES CREATION FORM
// ==============================================================================

/**
 * Shows the modal dialog for creating a new timeseries record.
 */
function showNewTimeseriesForm() {
  return TimeseriesService.showCreateForm();
}

/**
 * Server-side handler for the new timeseries form submission.
 * 1. Pushes the record to the API immediately.
 * 2. Fetches the complete new record (with ID) from the API using specific Code Fetch.
 * 3. Inserts the complete record into the Timeseries sheet.
 */
function processNewTimeseriesForm(formObject) {
  return TimeseriesService.processCreateForm(formObject);
}

/**
 * Returns the HTML content for the timeseries creation form.
 */
function getNewTimeseriesFormHtml() {
  return TimeseriesService.getCreateFormHtml();
}

// ==============================================================================
// UTILITY: API and Sheet Helpers
// ==============================================================================

/**
 * Helper to convert a Date object to a yyyy-MM-dd string.
 * @param {Date} date The date object.
 * @returns {string} The formatted date string.
 */
function toDateStr(date) {
    const y = date.getFullYear();
    const m = date.getMonth() + 1;
    const d = date.getDate();
    return y + "-" + (m < 10 ? "0" + m : m) + "-" + (d < 10 ? "0" + d : d);
}

/**
 * Retrieves the base API URL from the API_URL named range.
 * @param {GoogleAppsScript.Spreadsheet.Spreadsheet} ss The active spreadsheet.
 * @returns {string | null} The base API URL or null if not found.
 */
function getApiUrl(ss) {
    return App.getApiUrl();
}

/**
 * Helper function to build the full API URL.
 * @param {string} baseUrl The base API URL.
 * @param {string} path The API path suffix.
 * @returns {string} The complete API URL.
 */
function buildApiUrl(baseUrl, path) {
    return App.buildUrl(baseUrl, path);
}

/**
 * Fetches JSON data with simple error handling.
 * @param {string} url The URL to fetch.
 * @param {GoogleAppsScript.URL_Fetch.URLFetchRequestOptions} options The fetch options.
 * @returns {Object} The parsed JSON object.
 * @throws {Error} If fetching fails.
 */
function fetchJsonWithRetry(url, options) {
    return App.fetchJson(url, options);
}

/**
 * Fetches data (non-JSON response expected, or for POST requests where content matters less than status).
 * @param {string} url The URL to fetch.
 * @param {GoogleAppsScript.URL_Fetch.URLFetchRequestOptions} options The fetch options.
 * @returns {GoogleAppsScript.URL_Fetch.HTTPResponse} The HTTP response.
 * @throws {Error} If fetching fails.
 */
function fetchWithRetry(url, options) {
    return App.fetch(url, options);
}


/**
 * Writes table data to a sheet efficiently. Clears old data, writes headers and new data.
 * @param {GoogleAppsScript.Spreadsheet.Spreadsheet} ss The active spreadsheet.
 * @param {string} sheetName The name of the sheet.
 * @param {string[]} headers The column headers.
 * @param {any[][]} tableData The data rows.
 * @returns {GoogleAppsScript.Spreadsheet.Sheet} The sheet object.
 */
function writeTableFast(ss, sheetName, headers, tableData) {
    let sheet = ss.getSheetByName(sheetName);
    if (!sheet) {
        sheet = ss.insertSheet(sheetName);
    }
    
    const lastRow = sheet.getLastRow();
    const lastCol = sheet.getLastColumn();

    // Clear old data range (Rows 2 onwards)
    if (lastRow > 1 && lastCol > 0) {
      sheet.getRange(2, 1, lastRow, lastCol).clearContent();
    }
    
    // Clear old headers and write new headers
    sheet.clearFormats();
    sheet.getRange(1, 1, 1, lastCol > headers.length ? lastCol : headers.length).clearContent();
    sheet.getRange(1, 1, 1, headers.length).setValues([headers]);
    
    // Write Data
    if (tableData.length > 0) {
      sheet.getRange(2, 1, tableData.length, headers.length).setValues(tableData);
    }

    sheet.setFrozenRows(1);
    
    return sheet;
}
