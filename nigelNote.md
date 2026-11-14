# we need an endpoint so the astronaut could upload their health history that we could use a baseline

# singular channel/parameter reading shape (see docs/backend_contract.md) 

units are assumed to be from SI standard
{                                                                     
"channel": "bp_systolic",
"value": 15732.0,
"unit": "Pa",
"measured_at": "2026-11-08T07:12:00Z"
}                                                                                                                                                

# dictionary — environment-dependent, fetched once on environnmen switch
  {                                                                     
    "environment": { "id": "lunar_surface", "gravity_g": 0.166,
                     "comm_delay_s": 2.6 },
    "channels": [{
      "channel": "bp_systolic",
      "name": "Blood pressure (systolic)",
      "domain": "cardiovascular",
      "body_regions": ["heart", "chest"],
      "explanation": "Why this is measured, what it means…"
    }]                                                                                                                                                                                         
  }

  body_regions is what makes the clickable body figure a data-driven feature instead of a hardcoded SVG switch statement. citations per channel is what makes the pitch line in idea.md ("every
  threshold hardcoded from cited research") literally checkable by a judge — it's in the API.