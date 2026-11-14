/**
 * @fileoverview Financial Tracker Core Script - Unified & Optimized.
 * Built with SRP (Single Responsibility Principle).
 */

// ==========================================
// 1. CONFIGURATION
// ==========================================
const CONFIG = {
  ACTIVE_SHEETS: {
    OFER: "עופר",
    SHAY: "שי",
    HOME: "בית"
  },
  TEMPLATES: {
    "עופר": "שבלונה עופר",
    "שי": "שבלונה שי",
    "בית": "שבלונה בית"
  },
  MONTHS: [
    "ינואר", "פברואר", "מרץ", "אפריל", "מאי", "יוני",
    "יולי", "אוגוסט", "ספטמבר", "אוקטובר", "נובמבר", "דצמבר"
  ],
  LABELS: {
    HOME: "בית",
    MANDATORY: "חובה",
    ROUTINE: "שוטף",
    WEEKLY: "קניות שבועיות",
    FUEL: "דלק"
  },
  CONSTANTS: {
    HEADER_ROWS: 3,
    GAP_BEFORE_MONTH: 0
  }
};

// ==========================================
// 2. FORMULA SERVICE (ניהול נוסחאות)
// ==========================================
const FormulaService = {

  inject: function(sheet, startRow, sheetName) {
    if (sheetName === CONFIG.ACTIVE_SHEETS.HOME) {
      this.injectHomeFormulas(sheet, startRow);
    } else {
      // כאן הקוד מזהה שזה או עופר או שי ומפעיל את אותה לוגיקה
      this.injectPersonalFormulas(sheet, startRow);
    }
  },

/**
 * נוסחאות לגיליון הבית - גרסה סופית, מאוחדת וללא כפילויות
 */
injectHomeFormulas: function(sheet, startRow) {
  const lastRow = sheet.getLastRow();
  const rangeHeight = lastRow - startRow + 1;
  const dataA = sheet.getRange(startRow, 1, rangeHeight, 1).getValues();

  let shotefRow = -1;
  let weeklyRow = -1;
  let sikumRow = -1;

  // 1. איתור העוגנים בעמודה A
  for (let i = 0; i < dataA.length; i++) {
    const val = dataA[i][0].toString().trim();
    if (val === CONFIG.LABELS.ROUTINE) shotefRow = startRow + i;
    else if (val === CONFIG.LABELS.WEEKLY) weeklyRow = startRow + i;
    else if (val === "סיכום") {
      sikumRow = startRow + i;
      break;
    }
  }

  // 2. בדיקה שנמצאו העוגנים לפני הזרקת נוסחאות
  if (shotefRow !== -1 && weeklyRow !== -1 && sikumRow !== -1) {

    // הגדרת הטווח המאוחד עבור G: מהתחלה ועד שורה לפני "קניות שבועיות"
    // בדוגמה שלך: E97:E101
    const fixedArea = `E${startRow + 1}:E${weeklyRow - 1}`;

    // הגדרת טווח הקניות עבור E: משורה אחרי הכותרת ועד מעל ה"סיכום"
    // בדוגמה שלך: E103:E110
    const weeklyArea = `E${weeklyRow}:E${sikumRow - 1}`;

    // --- הזרקת הנוסחאות המדויקות ---

    // עמודה E: סכום הקניות השבועיות
    sheet.getRange(sikumRow, 5).setFormula(`=SUM(${weeklyArea})`);

    // עמודה G: הנוסחה המאוחדת שביקשת (קבועות + מה שבעמודה E)
    // התוצאה בגיליון: =SUM(E97:E101) + E111
    sheet.getRange(sikumRow, 7).setFormula(`=SUM(${fixedArea}) + E${sikumRow}`);

    // עיצוב ויזואלי
    sheet.getRange(sikumRow, 5).setFontWeight("bold").setBackground("#d9ead3");
    sheet.getRange(sikumRow, 7).setFontWeight("bold").setBackground("#fff2cc");

    Logger.log(`✅ סיכום בית הושלם: E (קניות), G (מאוחד: ${fixedArea})`);
  } else {
    Logger.log(`⚠️ אזהרה: לא ניתן היה להזריק נוסחאות בבית - חסרים עוגנים.`);
  }
},

/**
   * נוסחאות אישיות (עופר ושי) - קישור לבית + סיכומי קצה (סה"כ חודשי)
   */
  /**
   * שלב 1 ו-2 עם הדפסות עומק ורענון נתונים
   */
  injectPersonalFormulas: function(sheet, startRow) {
    const ss = SpreadsheetApp.getActiveSpreadsheet();
    // רענון כפוי כדי לוודא שכל מה שנכתב לבית עד כה "נחת" בגיליון
    SpreadsheetApp.flush();

    const homeSheet = ss.getSheetByName(CONFIG.ACTIVE_SHEETS.HOME);
    const fixedExpenses = ["שכר דירה", "חשמל", "מים", "גז", "ארנונה"];

    Logger.log(`--- 🔍 התחלת סנכרון לגיליון ${sheet.getName()} ---`);

    // שלב 1: איתור חודש בבית
    const homeLastRow = homeSheet.getLastRow();
    Logger.log(`📏 שורה אחרונה בבית לפי המערכת: ${homeLastRow}`);

    const homeStartRow = findMonthHeaderRow(homeSheet, homeLastRow);

    if (!homeStartRow) {
      Logger.log(`❌ שגיאה: לא נמצא חודש בגיליון הבית! נסה לבדוק אם עמודה A בבית מכילה את שם החודש.`);
      return;
    }

    Logger.log(`📍 נמצא חודש בבית בשורה: ${homeStartRow}`);

    // משיכת נתונים
    const homeRangeHeight = homeSheet.getLastRow() - homeStartRow + 1;
    const homeData = homeSheet.getRange(homeStartRow, 1, homeRangeHeight, 5).getValues();

    const rangeHeight = sheet.getLastRow() - startRow + 1;
    const blockData = sheet.getRange(startRow, 1, rangeHeight, 4).getValues();
    let totalMonthlyRow = -1;

    // שלב 2: סריקה והזרקה
    for (let i = 0; i < blockData.length; i++) {
      const colA = blockData[i][0].toString().trim();
      const colD = blockData[i][3].toString().trim();
      const currentRow = startRow + i;

      if (fixedExpenses.includes(colD)) {
        // מחפשים התאמה בעמודה D של הבית (אינדקס 3)
        const matchIdx = homeData.findIndex(row => row[3].toString().trim() === colD);
        if (matchIdx !== -1) {
          const targetHomeRow = homeStartRow + matchIdx;
          sheet.getRange(currentRow, 5).setFormula(`='${CONFIG.ACTIVE_SHEETS.HOME}'!E${targetHomeRow}/2`);
          Logger.log(`✅ קושר: ${colD} -> בית!E${targetHomeRow}`);
        }
      }

      if (colD === "קניות") {
        const sikumIdx = homeData.findIndex(row => row[0].toString().trim() === "סיכום");
        if (sikumIdx !== -1) {
          const targetHomeRow = homeStartRow + sikumIdx;
          sheet.getRange(currentRow, 5).setFormula(`='${CONFIG.ACTIVE_SHEETS.HOME}'!E${targetHomeRow}/2`);
          Logger.log(`✅ קושר: קניות -> סיכום בית ב-E${targetHomeRow}`);
        }
      }

      if (colA === "סה\"כ חודשי") totalMonthlyRow = currentRow;
    }

    // הזרקת נוסחאות סיכום (D, J, G)
    if (totalMonthlyRow !== -1) {
      const rangeE = `E${startRow + 1}:E${totalMonthlyRow - 1}`;
      const rangeJ = `J${startRow + 1}:J${totalMonthlyRow - 1}`;
      sheet.getRange(totalMonthlyRow, 4).setFormula(`=SUM(${rangeE})`);
      sheet.getRange(totalMonthlyRow, 10).setFormula(`=SUM(${rangeJ})`);
      sheet.getRange(totalMonthlyRow, 7).setFormula(`=J${totalMonthlyRow} - D${totalMonthlyRow}`);
      Logger.log(`🏁 סיכום חודשי הוזרק לשורה ${totalMonthlyRow}`);
    }
  }
}

function onEdit(e) {
  const range = e.range;
  const sheet = range.getSheet();
  const sheetName = sheet.getName();

  // בדיקה אם הגיליון פעיל (מחליף את isFinanceSheet)
  if (!Object.values(CONFIG.ACTIVE_SHEETS).includes(sheetName)) return;

  const startRow = range.getRow();
  const numRows = range.getNumRows();
  const startCol = range.getColumn();
  const numCols = range.getNumColumns();

  // בדיקת עמודות D או E (4-5) ומעל שורה 3
  if (!(startCol <= 5 && (startCol + numCols - 1) >= 4) || startRow <= CONFIG.CONSTANTS.HEADER_ROWS) return;

  for (let i = 0; i < numRows; i++) {
    const currentRow = startRow + i;
    const rowRange = sheet.getRange(currentRow, 1, 1, 5).getValues()[0];

    const context = {
      sheet: sheet,
      row: currentRow,
      category: rowRange[0], // עמודה A
      number: rowRange[1],   // עמודה B
      description: rowRange[3], // עמודה D
      amount: rowRange[4],      // עמודה E
      sheetName: sheetName
    };

    processRowUpdate(context);
  }
}

function processRowUpdate(context) {
  const { sheet, row, description, amount, category } = context;

  // מחיקה: ניקוי שורה אם תיאור וסכום ריקים
  if (description === "" && amount === "") {
    const protectedLabels = Object.values(CONFIG.LABELS);
    const isProtected = protectedLabels.includes(category.toString().trim());

    if (isProtected) {
      sheet.getRange(row, 2, 1, 2).clearContent();
    } else {
      sheet.getRange(row, 1, 1, 3).clearContent();
    }
    return;
  }

  // עדכון מספור (אם חסר)
  if (context.number === "") {
    const nextNum = calculateAutomaticNumber(context);
    if (nextNum) sheet.getRange(row, 2).setValue(nextNum);
  }

  // עדכון תאריך (אם חסר - מחליף את applyDateIfEmpty)
  const dateCell = sheet.getRange(row, 3);
  if (dateCell.getValue() === "") {
    dateCell.setValue(new Date()).setNumberFormat("dd/MM/yy");
  }
}

// ==========================================
// 4. AUTOMATION ENGINE
// ==========================================
function runMonthlyAutomation() {
  const monthTitle = getActiveMonthTitle();
  const ss = SpreadsheetApp.getActiveSpreadsheet();

  const executionOrder = [
    CONFIG.ACTIVE_SHEETS.HOME,
    CONFIG.ACTIVE_SHEETS.SHAY,
    CONFIG.ACTIVE_SHEETS.OFER
  ];

  executionOrder.forEach(sheetName => {
    const activeSheet = ss.getSheetByName(sheetName);
    const templateName = CONFIG.TEMPLATES[sheetName];

    if (activeSheet && templateName) {
      hidePreviousData(activeSheet);
      const startRow = deployTemplate(activeSheet, templateName, monthTitle);
      if (startRow) {
        FormulaService.inject(activeSheet, startRow, sheetName);
      }
    }
  });
}

// ==========================================
// 5. UTILITIES (פונקציות עזר)
// ==========================================

function getActiveMonthTitle() {
  const now = new Date();
  return `${CONFIG.MONTHS[now.getMonth()]} ${now.getFullYear()}`;
}

function deployTemplate(targetSheet, templateName, monthTitle) {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const templateSheet = ss.getSheetByName(templateName);

  if (!templateSheet) {
    Logger.log(`❌ שגיאה: לא נמצא גיליון שבלונה בשם ${templateName}`);
    return null;
  }

  const sourceStartRow = 4; // דילוג על כותרות השבלונה
  const lastRow = templateSheet.getLastRow();
  const lastCol = templateSheet.getLastColumn(); // לוקח את כל העמודות שיש בשבלונה

  if (lastRow < sourceStartRow) {
    Logger.log(`⚠️ אזהרה: השבלונה ${templateName} ריקה מתחת לשורה 3`);
    return null;
  }

  const numRows = lastRow - sourceStartRow + 1;

  // הגדרת טווח המקור - לוקח את כל העמודות הקימיות בשבלונה
  const sourceRange = templateSheet.getRange(sourceStartRow, 1, numRows, lastCol);

  // מציאת שורת היעד - מוודא שהיא לפחות מעל שורה 3
  let targetRow = targetSheet.getLastRow() + CONFIG.CONSTANTS.GAP_BEFORE_MONTH + 1;
  if (targetRow <= CONFIG.CONSTANTS.HEADER_ROWS) {
    targetRow = CONFIG.CONSTANTS.HEADER_ROWS + 1;
  }

  // ביצוע ההעתקה - כולל עיצוב, נוסחאות ומיזוגים
  const targetRange = targetSheet.getRange(targetRow, 1);
  sourceRange.copyTo(targetRange);

  // עדכון כותרת החודש בתא הראשון של הטבלה החדשה
  targetSheet.getRange(targetRow, 1).setValue(monthTitle);

  Logger.log(`✅ הועתקה שבלונה ${templateName} לשורה ${targetRow} בגיליון ${targetSheet.getName()}`);
  return targetRow;
}

function calculateAutomaticNumber(context) {
  const { sheet, row } = context;
  const cell = sheet.getRange(row, 1);
  let categoryValue = "";
  let categoryStartRow = row;

  // טיפול במיזוגים (מחליף את getCellValueWithMerged)
  if (cell.isPartOfMerge()) {
    const mergeRange = cell.getMergedRanges()[0];
    categoryValue = mergeRange.getCell(1, 1).getValue().toString().trim();
    categoryStartRow = mergeRange.getRow();
  } else {
    categoryValue = cell.getValue().toString().trim();
  }

  const monthStart = findMonthHeaderRow(sheet, row);
  if (!monthStart) return 1;

  if (Object.values(CONFIG.LABELS).includes(categoryValue)) {
    return (row - categoryStartRow) + 1;
  }

  const nearestAnchor = getNearestCategoryEndRow(sheet, categoryStartRow - 1, monthStart);
  return (nearestAnchor && row > nearestAnchor) ? (row - nearestAnchor) : 1;
}

function findMonthHeaderRow(sheet, currentRow) {
  if (currentRow <= 0) return null;

  // לוקחים את עמודות A ו-B ליתר ביטחון
  const displayValues = sheet.getRange(1, 1, currentRow, 2).getDisplayValues();

  Logger.log(`🔎 מתחיל סריקה עמוקה על ${currentRow} שורות...`);

  for (let i = currentRow - 1; i >= 0; i--) {
    const valA = displayValues[i][0].toString().trim();
    const valB = displayValues[i][1].toString().trim();
    const rowNum = i + 1;

    // הדפסת debug מיוחדת לשורות שאינן ריקות כדי שנבין מה הולך שם
    if (valA !== "" || valB !== "") {
      // אם אנחנו באיזור של שורה 96 (איפה שהשבלונה התחילה), בוא נראה מה יש שם
      if (rowNum >= 90 && rowNum <= 100) {
        Logger.log(`🧐 בדיקה בשורה ${rowNum}: עמודה A=["${valA}"], עמודה B=["${valB}"]`);
      }
    }

    // הבדיקה האמיתית - האם אחד החודשים נמצא באחת העמודות?
    const foundMonth = CONFIG.MONTHS.find(m => valA.includes(m) || valB.includes(m));

    if (foundMonth) {
      Logger.log(`🎯 בינגו! נמצא החודש "${foundMonth}" בשורה ${rowNum}`);
      return rowNum;
    }
  }

  Logger.log(`❌ סיימתי לסרוק ולא מצאתי שום חודש מרשימת CONFIG.MONTHS`);
  return null;
}

function getNearestCategoryEndRow(sheet, startSearchFrom, monthStart) {
  if (startSearchFrom < monthStart) return null;
  const values = sheet.getRange(monthStart, 1, startSearchFrom - monthStart + 1, 1).getValues();
  const labels = Object.values(CONFIG.LABELS);

  for (let i = values.length - 1; i >= 0; i--) {
    if (labels.includes(values[i][0].toString().trim())) {
      const cell = sheet.getRange(monthStart + i, 1);
      return cell.isPartOfMerge() ? cell.getMergedRanges()[0].getLastRow() : monthStart + i;
    }
  }
  return null;
}

function hidePreviousData(sheet) {
  const lastRow = sheet.getLastRow();
  const start = CONFIG.CONSTANTS.HEADER_ROWS + 1; // שורה 4

  if (lastRow < start) return;

  // איתור שורת ההתחלה של החודש האחרון שקיים כרגע בגיליון
  const latestExistingMonthRow = findMonthHeaderRow(sheet, lastRow);

  // אם יש חודשים ישנים יותר לפניו – מסתירים רק אותם
  if (latestExistingMonthRow && latestExistingMonthRow > start) {
    const rowsToHide = latestExistingMonthRow - start;
    sheet.hideRows(start, rowsToHide);
    Logger.log(`👁️ הוסתרו שורות ${start} עד ${latestExistingMonthRow - 1} בגיליון ${sheet.getName()} (החודש הקודם נשאר גלוי)`);
  } else {
    Logger.log(`ℹ️ לא נמצאו חודשים ישנים יותר להסתרה בגיליון ${sheet.getName()}`);
  }
}
