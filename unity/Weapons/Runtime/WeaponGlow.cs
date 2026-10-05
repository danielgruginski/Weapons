using UnityEngine;
using UnityEngine.Rendering;

namespace Weapons
{
    /// <summary>What an enchanted weapon is enchanted with: its runes' colour and the effect that comes off it.</summary>
    public enum Enchant { None, Flame, Frost, Storm, Venom, Holy, Arcane }

    /// <summary>
    /// The glow of an enchanted weapon (a "_Rune" model on M_Weapons_Rune): its runes and stones (T_Weapons_Glow, the
    /// emission map) light up in the enchantment's colour and breathe, a small light goes with them, and particles come
    /// off the blade: embers rise from flame, frost motes drift down, sparks crack off a storm weapon, venom drips, holy
    /// and arcane motes float. Effect objects are named FX_* (the goblins' merge leaves those out). Call
    /// <see cref="Set"/> to change the enchantment at run time.
    /// </summary>
    [DisallowMultipleComponent]
    [ExecuteAlways]
    public class WeaponGlow : MonoBehaviour
    {
        public Enchant element = Enchant.Arcane;
        [Tooltip("Use the element's own colour; off: the colour below.")]
        public bool elementColour = true;
        public Color colour = Color.white;
        [Tooltip("Emission strength of the runes (HDR multiplier).")]
        [Min(0f)] public float intensity = 5f;
        [Tooltip("How much the glow breathes (0: steady).")]
        [Range(0f, 1f)] public float pulse = 0.3f;
        public bool sparks = true;
        public bool glowLight = true;
        [Tooltip("Additive particle material (WeaponsSetup makes M_Weapons_Spark); empty: one is made at run time.")]
        public Material sparkMaterial;

        static readonly int EmissionId = Shader.PropertyToID("_EmissionColor");
        static Material fallbackSpark;
        MaterialPropertyBlock mpb;
        Renderer rend;
        ParticleSystem ps;
        Light lt;
        float seed;
        bool dirty = true;
        Enchant built = (Enchant)(-1);

        public Color Colour => elementColour ? ElementColour(element) : colour;

        public static Color ElementColour(Enchant e)
        {
            switch (e)
            {
                case Enchant.Flame: return new Color(1f, 0.42f, 0.1f);
                case Enchant.Frost: return new Color(0.45f, 0.82f, 1f);
                case Enchant.Storm: return new Color(0.72f, 0.64f, 1f);
                case Enchant.Venom: return new Color(0.4f, 0.95f, 0.2f);
                case Enchant.Holy: return new Color(1f, 0.85f, 0.45f);
                case Enchant.Arcane: return new Color(0.48f, 0.42f, 1f);
                default: return Color.white;
            }
        }

        /// <summary>enchant it with this (and its own colour, or the one given)</summary>
        public void Set(Enchant e, Color? c = null)
        {
            element = e;
            elementColour = c == null;
            if (c != null) colour = c.Value;
            dirty = true;
            Apply(0f);
        }

        void OnEnable()
        {
            seed = Random.value * 10f;
            dirty = true;
            Apply(0f);
        }

        void OnValidate() => dirty = true;

        void OnDisable()
        {
            if (rend != null) rend.SetPropertyBlock(null);
        }

        void Update() => Apply(Application.isPlaying ? Time.time : (float)Time.realtimeSinceStartupAsDouble);

        void Apply(float t)
        {
            if (rend == null) rend = GetComponent<Renderer>();
            if (rend == null) return;
            if (dirty || built != element) Build();
            var c = Colour;
            float k = 1f + pulse * Mathf.Sin(t * 2.2f + seed);
            if (element == Enchant.Storm) k *= Mathf.PerlinNoise(t * 9f, seed) > 0.72f ? 1.9f : 0.85f;   // crackle
            if (element == Enchant.Flame) k *= 0.85f + 0.3f * Mathf.PerlinNoise(t * 4f, seed);
            if (mpb == null) mpb = new MaterialPropertyBlock();
            rend.GetPropertyBlock(mpb);
            mpb.SetColor(EmissionId, element == Enchant.None ? Color.black : c.linear * (intensity * k));
            rend.SetPropertyBlock(mpb);
            if (lt != null)
            {
                lt.color = c;
                lt.intensity = 1.1f * k;
            }
        }

        void Build()
        {
            dirty = false;
            built = element;
            var c = Colour;
            lt = Child<Light>("FX_Light", glowLight && element != Enchant.None);
            if (lt != null)
            {
                lt.type = LightType.Point;
                lt.range = 2.2f;
                lt.shadows = LightShadows.None;
                lt.transform.localPosition = new Vector3(0f, LengthUp() * 0.55f, 0f);
            }
            ps = Child<ParticleSystem>("FX_Sparks", sparks && element != Enchant.None);
            if (ps != null) Configure(ps, element, c);
        }

        float LengthUp()
        {
            var mf = GetComponent<MeshFilter>();
            return mf != null && mf.sharedMesh != null ? mf.sharedMesh.bounds.max.y : 0.5f;
        }

        T Child<T>(string name, bool want) where T : Component
        {
            var t = transform.Find(name);
            if (!want)
            {
                if (t != null)
                {
                    if (Application.isPlaying) Destroy(t.gameObject);
                    else DestroyImmediate(t.gameObject);
                }
                return null;
            }
            if (t == null)
            {
                t = new GameObject(name).transform;
                t.SetParent(transform, false);
            }
            var comp = t.GetComponent<T>();
            return comp != null ? comp : t.gameObject.AddComponent<T>();
        }

        void Configure(ParticleSystem p, Enchant e, Color c)
        {
            var main = p.main;
            main.simulationSpace = ParticleSystemSimulationSpace.World;
            main.scalingMode = ParticleSystemScalingMode.Shape;
            main.playOnAwake = true;
            main.loop = true;
            main.maxParticles = 120;
            var em = p.emission;
            var shape = p.shape;
            var mr = GetComponent<MeshRenderer>();
            if (mr != null)
            {
                shape.shapeType = ParticleSystemShapeType.MeshRenderer;
                shape.meshRenderer = mr;
                shape.meshShapeType = ParticleSystemMeshShapeType.Triangle;
            }
            else shape.shapeType = ParticleSystemShapeType.Sphere;
            var col = p.colorOverLifetime;
            col.enabled = true;
            var grad = new Gradient();
            var size = p.sizeOverLifetime;
            size.enabled = true;
            size.size = new ParticleSystem.MinMaxCurve(1f, AnimationCurve.EaseInOut(0f, 1f, 1f, 0.2f));
            var noise = p.noise;
            noise.enabled = false;
            Color hot = Color.Lerp(c, Color.white, 0.5f);
            switch (e)
            {
                case Enchant.Flame:                      // embers that rise and redden
                    main.startLifetime = new ParticleSystem.MinMaxCurve(0.45f, 0.9f);
                    main.startSpeed = new ParticleSystem.MinMaxCurve(0.02f, 0.12f);
                    main.startSize = new ParticleSystem.MinMaxCurve(0.03f, 0.065f);
                    main.gravityModifier = -0.12f;
                    em.rateOverTime = 44f;
                    grad.SetKeys(new[] { new GradientColorKey(hot, 0f), new GradientColorKey(c, 0.4f), new GradientColorKey(new Color(0.8f, 0.12f, 0.05f), 1f) },
                                 new[] { new GradientAlphaKey(0f, 0f), new GradientAlphaKey(1f, 0.15f), new GradientAlphaKey(0f, 1f) });
                    noise.enabled = true; noise.strength = 0.25f; noise.frequency = 2f;
                    break;
                case Enchant.Frost:                      // cold motes drifting down
                    main.startLifetime = new ParticleSystem.MinMaxCurve(0.9f, 1.6f);
                    main.startSpeed = new ParticleSystem.MinMaxCurve(0.0f, 0.03f);
                    main.startSize = new ParticleSystem.MinMaxCurve(0.022f, 0.045f);
                    main.gravityModifier = 0.03f;
                    em.rateOverTime = 28f;
                    grad.SetKeys(new[] { new GradientColorKey(Color.white, 0f), new GradientColorKey(c, 1f) },
                                 new[] { new GradientAlphaKey(0f, 0f), new GradientAlphaKey(0.9f, 0.2f), new GradientAlphaKey(0f, 1f) });
                    break;
                case Enchant.Storm:                      // short sparks cracking off
                    main.startLifetime = new ParticleSystem.MinMaxCurve(0.06f, 0.18f);
                    main.startSpeed = new ParticleSystem.MinMaxCurve(0.4f, 1.1f);
                    main.startSize = new ParticleSystem.MinMaxCurve(0.014f, 0.032f);
                    main.gravityModifier = 0f;
                    em.rateOverTime = 64f;
                    shape.randomDirectionAmount = 1f;
                    grad.SetKeys(new[] { new GradientColorKey(Color.white, 0f), new GradientColorKey(c, 1f) },
                                 new[] { new GradientAlphaKey(1f, 0f), new GradientAlphaKey(0f, 1f) });
                    break;
                case Enchant.Venom:                      // drops that fall
                    main.startLifetime = new ParticleSystem.MinMaxCurve(0.5f, 0.9f);
                    main.startSpeed = 0f;
                    main.startSize = new ParticleSystem.MinMaxCurve(0.02f, 0.036f);
                    main.gravityModifier = 0.35f;
                    em.rateOverTime = 20f;
                    grad.SetKeys(new[] { new GradientColorKey(hot, 0f), new GradientColorKey(c, 1f) },
                                 new[] { new GradientAlphaKey(0f, 0f), new GradientAlphaKey(1f, 0.1f), new GradientAlphaKey(0f, 1f) });
                    break;
                case Enchant.Holy:                       // warm motes rising slowly
                    main.startLifetime = new ParticleSystem.MinMaxCurve(1.0f, 1.6f);
                    main.startSpeed = new ParticleSystem.MinMaxCurve(0.0f, 0.04f);
                    main.startSize = new ParticleSystem.MinMaxCurve(0.026f, 0.05f);
                    main.gravityModifier = -0.04f;
                    em.rateOverTime = 22f;
                    grad.SetKeys(new[] { new GradientColorKey(Color.white, 0f), new GradientColorKey(c, 1f) },
                                 new[] { new GradientAlphaKey(0f, 0f), new GradientAlphaKey(0.8f, 0.3f), new GradientAlphaKey(0f, 1f) });
                    break;
                default:                                 // arcane: motes that wander
                    main.startLifetime = new ParticleSystem.MinMaxCurve(0.8f, 1.3f);
                    main.startSpeed = new ParticleSystem.MinMaxCurve(0.0f, 0.05f);
                    main.startSize = new ParticleSystem.MinMaxCurve(0.02f, 0.042f);
                    main.gravityModifier = 0f;
                    em.rateOverTime = 30f;
                    grad.SetKeys(new[] { new GradientColorKey(hot, 0f), new GradientColorKey(c, 1f) },
                                 new[] { new GradientAlphaKey(0f, 0f), new GradientAlphaKey(1f, 0.25f), new GradientAlphaKey(0f, 1f) });
                    noise.enabled = true; noise.strength = 0.15f; noise.frequency = 1.5f;
                    break;
            }
            main.startColor = Color.white;
            col.color = grad;
            var r = p.GetComponent<ParticleSystemRenderer>();
            r.renderMode = ParticleSystemRenderMode.Billboard;
            r.shadowCastingMode = ShadowCastingMode.Off;
            r.receiveShadows = false;
            r.sharedMaterial = sparkMaterial != null ? sparkMaterial : FallbackSpark();
            if (!p.isPlaying) p.Play();
        }

        /// <summary>URP Particles/Unlit, additive, a soft round dot</summary>
        public static Material FallbackSpark()
        {
            if (fallbackSpark != null) return fallbackSpark;
            var sh = Shader.Find("Universal Render Pipeline/Particles/Unlit") ?? Shader.Find("Sprites/Default");
            var m = new Material(sh) { name = "WeaponSpark" };
            MakeAdditive(m, DotTexture());
            return fallbackSpark = m;
        }

        public static void MakeAdditive(Material m, Texture tex)
        {
            m.SetFloat("_Surface", 1f);
            m.SetFloat("_Blend", 2f);
            m.SetFloat("_SrcBlend", (float)BlendMode.SrcAlpha);
            m.SetFloat("_DstBlend", (float)BlendMode.One);
            m.SetFloat("_SrcBlendAlpha", (float)BlendMode.One);
            m.SetFloat("_DstBlendAlpha", (float)BlendMode.One);
            m.SetFloat("_ZWrite", 0f);
            m.SetFloat("_Cull", 0f);
            m.SetOverrideTag("RenderType", "Transparent");
            m.EnableKeyword("_SURFACE_TYPE_TRANSPARENT");
            m.renderQueue = (int)RenderQueue.Transparent;
            m.SetTexture("_BaseMap", tex);
            m.mainTexture = tex;
            m.SetColor("_BaseColor", Color.white);
        }

        /// <summary>white, alpha falling off from a bright core</summary>
        public static Texture2D DotTexture(int size = 64)
        {
            var tex = new Texture2D(size, size, TextureFormat.RGBA32, true) { name = "WeaponSparkDot", wrapMode = TextureWrapMode.Clamp };
            var px = new Color32[size * size];
            for (int y = 0; y < size; y++)
                for (int x = 0; x < size; x++)
                {
                    float dx = (x + 0.5f) / size * 2f - 1f, dy = (y + 0.5f) / size * 2f - 1f;
                    float d = Mathf.Sqrt(dx * dx + dy * dy);
                    float a = Mathf.Pow(Mathf.Clamp01(1f - d), 2.4f) + 0.7f * Mathf.Pow(Mathf.Clamp01(1f - d * 2.6f), 2f);
                    px[y * size + x] = new Color32(255, 255, 255, (byte)(Mathf.Clamp01(a) * 255));
                }
            tex.SetPixels32(px);
            tex.Apply(true);
            return tex;
        }
    }
}
