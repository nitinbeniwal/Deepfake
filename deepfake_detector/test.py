from takedown import generate_legal_report

# Generate a test report
report_path = generate_legal_report(
    url="https://www.example.com/fake-video",
    confidence=91.5
)

print(f"\nOpen the reports folder to see your PDF!")