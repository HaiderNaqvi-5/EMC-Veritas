export function StudentPortal() {
  return (
    <main className="student-portal">
      <header className="brand-bar" aria-label="Institutional branding">
        <img src="/assets/logos/nfc-iet-logo.png" alt="NFC-IET Multan" />
        <img src="/assets/logos/emc-logo.png" alt="Event Management Club" />
      </header>
      <section className="lookup-card">
        <p className="eyebrow">Event Management Club · NFC-IET Multan</p>
        <h1>EMC Veritas</h1>
        <p>Enter your roll number to find available certificates and recognition letters.</p>
        <form>
          <label htmlFor="roll-number">Roll number</label>
          <input id="roll-number" name="roll-number" autoComplete="off" required />
          <button type="submit">Find documents</button>
        </form>
      </section>
    </main>
  );
}
