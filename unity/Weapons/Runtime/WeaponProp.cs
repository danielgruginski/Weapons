using UnityEngine;

namespace Weapons
{
    /// <summary>
    /// What the weapon kit knows about one of its props (from export/weapons.json): which hand holds it and the points a
    /// game needs, all in the prop's own space. Props are modelled in the goblins' socket frame: origin where the fist
    /// closes, +Y along the handle toward the business end, the knuckles' side (an edge, an axe's bit) on -X in Unity.
    /// </summary>
    [DisallowMultipleComponent]
    public class WeaponProp : MonoBehaviour
    {
        [Tooltip("R: the right fist; L: the left fist (bows, crossbows); M: a missile (arrow, bolt; +Y along the flight).")]
        public string hand = "R";
        [Tooltip("A bow's string runs between these (none when they are the same).")]
        public Vector3 stringTop, stringBottom;
        [Tooltip("Where a crossbow's bolt lies, loaded.")]
        public Vector3 boltRest;
        [Tooltip("Length along +Y (m).")]
        public float length;
        public int triangles;
        [Tooltip("The enchanted model: its runes and stones glow through WeaponGlow.")]
        public bool runed;
    }
}
