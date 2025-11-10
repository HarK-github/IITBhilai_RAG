export default async function handler(req, res) {
  const { question } = req.query;

  try { 
    const response = await fetch(`http://127.0.0.1:8000/chat?question=${encodeURIComponent(question)}`);
    const data = await response.json();
    res.status(200).json(data);
  } catch (err) {
    res.status(500).json({ response: "Error connecting to AI server" });
  }
}
