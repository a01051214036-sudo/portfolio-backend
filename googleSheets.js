import { google } from "googleapis";

/**
 * 구글 시트에서 데이터 읽어서
 * [{ account, category, assetClass, ... }] 형태로 반환
 */
export async function getSheetData() {
  // 🔐 서비스 계정 인증
  const auth = new google.auth.JWT(
    process.env.GOOGLE_CLIENT_EMAIL,
    null,
    process.env.GOOGLE_PRIVATE_KEY.replace(/\\n/g, "\n"),
    ["https://www.googleapis.com/auth/spreadsheets.readonly"]
  );

  const sheets = google.sheets({ version: "v4", auth });

  // 📌 시트 정보
  const spreadsheetId = process.env.SPREADSHEET_ID;
  const range = "Sheet1!A1:J"; 
  // ↑ 컬럼 개수 정확히 맞춰줘 (A~J = 10개)

  const res = await sheets.spreadsheets.values.get({
    spreadsheetId,
    range,
  });

  const rows = res.data.values;

  if (!rows || rows.length < 2) {
    return [];
  }

  // 1행 = 헤더
  const headers = rows[0];

  // 2행부터 데이터
  const data = rows.slice(1).map((row) => {
    const obj = {};

    headers.forEach((header, index) => {
      let value = row[index] ?? "";

      // 🔢 숫자로 써야 하는 컬럼들
      if (["qty", "avgPrice", "currentPrice"].includes(header)) {
        value = value === "" ? null : Number(value);
      }

      obj[header] = value;
    });

    return obj;
  });

  return data;
}
