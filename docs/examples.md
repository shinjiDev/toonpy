# Examples

## JSON → TOON

Input (`examples/example1.json`):

```json
{
  "crew": [
    {"id": 1, "name": "Luz", "role": "Light glyph"},
    {"id": 2, "name": "Amity", "role": "Abomination strategist"}
  ],
  "active": true,
  "ship": {
    "name": "Owl House",
    "location": "Bonesborough"
  }
}
```

Serialized TOON:

```
crew[2]{id,name,role}:
  1,Luz,"Light glyph"
  2,Amity,"Abomination strategist"
active: true
ship:
  name: "Owl House"
  location: Bonesborough
```

## TOON → JSON

```
spell:
  name: light
  glyphs:
    - shape: circle
      layer: base
    - shape: triangle
      layer: focus
meta:
  created: 2024-08-01T10:00:00Z
  valid: true
```

Parsing the snippet above yields:

```json
{
  "spell": {
    "name": "light",
    "glyphs": [
      {"shape": "circle", "layer": "base"},
      {"shape": "triangle", "layer": "focus"}
    ]
  },
  "meta": {
    "created": "2024-08-01T10:00:00Z",
    "valid": true
  }
}
```

## Comments and Multiline Strings

```
/*
  The following description spans multiple lines.
*/
entry:
  id: 7
  description: """
This glyph was recovered
near Eclipse Lake.
"""
```

The parser preserves the newline characters within `description`.

