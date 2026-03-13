"""Email intake tool — handles email parsing and sample email loading."""
from __future__ import annotations

SAMPLE_EMAILS = {
    "auto_accident": {
        "from": "tom.rezac@email.com",
        "to": "claims@prairieshield.com",
        "subject": "Car accident this morning",
        "body": """Hi Lisa,

I was in an accident this morning on my way to work. I was stopped at the light at 72nd and Dodge and someone ran the red light and rear-ended me. Pretty hard hit. My truck (the F-150) has bumper damage and the tailgate won't close properly. I think the frame might be bent too.

The other driver's name is Maria Gonzales, she has State Farm. I got her info and the police came and made a report. I can get you the report number once they file it — the officer said it would be available in a couple days. OPD case number is 2024-889431.

No one was hurt thankfully, just shook up. The truck is still drivable but it doesn't feel right.

My policy number is AO-PA-8847321.

Let me know what I need to do next.

Thanks,
Tom"""
    },
    "hail_damage": {
        "from": "linda.sorensen@outlook.com",
        "to": "claims@prairieshield.com",
        "subject": "Hail damage from last night's storm",
        "body": """Mark,

We got hit hard with that storm last night. The hail was huge — bigger than golf balls. Started around 9:30 PM and went on for maybe 20 minutes.

The roof is definitely damaged, I can see broken shingles from the ground and there's some in the yard. The siding on the north side of the house has dents everywhere. Both skylights in the upstairs bathroom are cracked and I'm worried about leaking if it rains again.

The gutters on the east side are smashed too. My neighbor said his adjuster told him the whole neighborhood is going to need roofs.

I took some pictures this morning, I can email those over. Should I get a roofer out for an estimate or wait for the insurance adjuster?

My husband and I are just sick about it. That roof was only 5 years old.

Linda Sorensen
Policy: I don't have it in front of me but you should have it on file
912 W 4th St, Grand Island
(308) 555-0123"""
    },
    "farm_loss": {
        "from": "schroeder.farm@yahoo.com",
        "to": "claims@prairieshield.com",
        "subject": "Storm damage — barn and grain bins",
        "body": """Mark, it's Jim Schroeder calling — well, emailing. Nancy said I should email you so there's a record.

We had severe storms come through yesterday evening around 6 PM. Straight-line winds, the weather service said 70-80 mph. The north barn — the older one, not the new steel building — the west wall caved in and part of the roof came down. That barn still had some hay and a couple pieces of older equipment in it.

Two of the grain bins are dented pretty bad. One of them the roof is pushed in and I don't know if it's going to hold. They're empty right now thank god but harvest is coming.

Also lost about 400 feet of fence along Highway 81. A dozen head got out but the neighbors helped us round them all up. Everyone's accounted for, cattle are fine.

No one was hurt. Just a hell of a mess out here.

Our policy number is GM-FR-NE-445672. This is through Grinnell Mutual I believe.

Call me when you get a chance. I'll be out here all day cleaning up.

Jim
402-555-0512"""
    },
    "commercial_vehicle": {
        "from": "dispatch@gptrucking.com",
        "to": "claims@prairieshield.com",
        "subject": "URGENT — Truck accident on I-80 near Kearney",
        "body": """Mark,

We need to file a claim immediately. One of our trucks jackknifed on I-80 just west of Kearney this afternoon around 2 PM. The roads were icy and the rig went sideways.

Driver is Randy Becker Jr. He's okay but went to the hospital in Kearney (Good Samaritan) to get checked out. They're saying bruised ribs and some cuts. He's been released.

The truck is a 2021 Freightliner Cascadia, unit 7. It's been towed to the TA truck stop in Kearney. Trailer was loaded with farm equipment heading to a dealer in Denver — I need to call the shipper about the cargo.

Nebraska State Patrol was on scene. Report number is NSP-2025-00412.

This is on our commercial auto policy with EMC, policy number EMC-CA-BZ-331205.

Please get this to the carrier ASAP. With the injury involved I know they'll want to get on it quick.

Randy Becker Sr.
Great Plains Trucking
(402) 555-0945"""
    },
    "incomplete_claim": {
        "from": "mtorres84@gmail.com",
        "to": "claims@prairieshield.com",
        "subject": "my car got broken into",
        "body": """Hi I need to file a claim. Someone broke into my car last night and stole a bunch of stuff. They smashed the back window. This happened at my apartment on Vinton Street.

Can you help me with this?

Miguel"""
    },
}


def get_sample_email(scenario: str) -> dict | None:
    """Get a pre-written sample email for a demo scenario."""
    return SAMPLE_EMAILS.get(scenario)


def list_scenarios() -> list[dict]:
    """List available demo scenarios."""
    return [
        {"id": "auto_accident", "name": "Auto Accident", "description": "Tom Rezac — rear-ended at 72nd & Dodge"},
        {"id": "hail_damage", "name": "Hail Damage", "description": "Linda Sorensen — severe hail in Grand Island"},
        {"id": "farm_loss", "name": "Farm Loss", "description": "Jim Schroeder — barn and grain bin wind damage"},
        {"id": "commercial_vehicle", "name": "Commercial Vehicle", "description": "Great Plains Trucking — I-80 jackknife with injuries"},
        {"id": "incomplete_claim", "name": "Incomplete Claim", "description": "Miguel Torres — car break-in, missing details"},
    ]
