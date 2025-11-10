import { NextRequest, NextResponse } from "next/server";

export async function GET(request:NextRequest) {
  const question = request.nextUrl.searchParams.get("question");

  try {
    const response = await fetch(
      `http://127.0.0.1:8000/chat?question=${encodeURIComponent(question)}`
    );

    if (!response.ok) {
      throw new Error("Backend error");
    }

    const data = await response.json();

    console.log(data)
    // Return only the answer 
    return NextResponse.json({ answer: data.answer || data });
  } catch (err) {
    console.error(err);
    return NextResponse.json(
      { answer: "Error fetching data from backend" },
      { status: 500 }
    );
  }
}
