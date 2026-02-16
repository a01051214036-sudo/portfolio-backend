import express from "express";
import cors from "cors";
import { getSheetData } from "./googleSheets.js";

const app = express();
app.use(cors());

app.get("/api/data", async (req, res) => {
  try {
    const data = await getSheetData();
    res.json(data);
  } catch (err) {
    console.error(err);
    res.status(500).json({ error: "Failed to fetch sheet data" });
  }
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
});
