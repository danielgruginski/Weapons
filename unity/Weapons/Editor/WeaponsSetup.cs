using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;

namespace Weapons.EditorTools
{
    /// <summary>
    /// Tools > Weapons > Rebuild Prefabs and Showcase: from what tools/install_to_unity.ps1 copied into Assets/Weapons
    /// (Models/*.fbx, Models/weapons.json and shields.json, Textures/*.png) it makes the materials (M_Weapons; M_Weapons_Rune,
    /// the same with the glow map as emission, for the enchanted models; M_Shields and M_Shields_Rune over the shields'
    /// own atlas; M_Weapons_Spark for the particles), one prefab per model (Prefabs/Wpn_*.prefab and Shd_*.prefab: mesh,
    /// material, WeaponProp; WeaponGlow on the enchanted ones) and the Weapons_Showcase scene, then renders it to
    /// Logs/WeaponsSetup.
    /// </summary>
    public static class WeaponsSetup
    {
        public const string Root = "Assets/Weapons";
        const string Models = Root + "/Models";
        const string Textures = Root + "/Textures";
        const string Materials = Root + "/Materials";
        const string Prefabs = Root + "/Prefabs";
        const string Scenes = Root + "/Scenes";
        const string Manifest = Models + "/weapons.json";
        const string ShieldManifest = Models + "/shields.json";
        static string OutDir => Path.Combine(Path.GetDirectoryName(Application.dataPath), "Logs", "WeaponsSetup");

        [Serializable]
        class Entry
        {
            public string name, hand;
            public int tris;
            public float length;
            public bool runed;
            public float[] bounds_min, bounds_max, string_top, string_bottom, bolt_rest;
        }

        [Serializable]
        class ManifestFile { public Entry[] weapons, shields; }

        /// <summary>a shield (hand "S"): on the shields' atlas, strapped to Socket_Shield</summary>
        static bool IsShield(Entry e) => e.hand == "S";

        [MenuItem("Tools/Weapons/Rebuild Prefabs and Showcase")]
        public static void RebuildMenu() => Debug.Log(Rebuild(true));

        [MenuItem("Tools/Weapons/Rebuild Prefabs Only")]
        public static void PrefabsMenu() => Debug.Log(Rebuild(false));

        public static string Rebuild(bool showcase)
        {
            var log = new StringBuilder("[WeaponsSetup]\n");
            var list = Load();
            if (list == null) return $"no {Manifest}: run tools/install_to_unity.ps1 first";
            foreach (var d in new[] { Materials, Prefabs, Scenes })
                if (!AssetDatabase.IsValidFolder(d)) AssetDatabase.CreateFolder(Root, Path.GetFileName(d));
            var plain = Lit("M_Weapons", false, "T_Weapons");
            var rune = Lit("M_Weapons_Rune", true, "T_Weapons");
            var shield = Lit("M_Shields", false, "T_Shields");
            var shieldRune = Lit("M_Shields_Rune", true, "T_Shields");
            var spark = Spark();
            int made = 0, tris = 0;
            foreach (var e in list)
            {
                var go = Prefab(e, IsShield(e) ? (e.runed ? shieldRune : shield) : e.runed ? rune : plain, spark);
                if (go != null) { made++; tris += e.tris; }
                else log.AppendLine($"  missing model {e.name}");
            }
            AssetDatabase.SaveAssets();
            log.AppendLine($"  {made} prefabs in {Prefabs} ({tris} triangles in all; materials M_Weapons, M_Weapons_Rune, M_Shields, M_Shields_Rune, M_Weapons_Spark)");
            if (showcase) log.AppendLine(BuildShowcase(list));
            return log.ToString();
        }

        static List<Entry> Load()
        {
            if (!File.Exists(Manifest)) return null;
            var m = JsonUtility.FromJson<ManifestFile>(File.ReadAllText(Manifest));
            var list = m?.weapons?.ToList();
            if (list != null && File.Exists(ShieldManifest))
            {
                var s = JsonUtility.FromJson<ManifestFile>(File.ReadAllText(ShieldManifest));
                if (s?.shields != null) list.AddRange(s.shields);
            }
            return list;
        }

        static Vector3 V(float[] a) => a != null && a.Length == 3 ? new Vector3(a[0], a[1], a[2]) : Vector3.zero;

        // ------------------------------------------------------------------------------------------------- materials
        static Material Lit(string name, bool emissive, string tex)
        {
            var path = $"{Materials}/{name}.mat";
            var shader = GraphicsSettings.currentRenderPipeline != null ? GraphicsSettings.currentRenderPipeline.defaultShader
                                                                        : Shader.Find("Standard");
            var m = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (m == null)
            {
                m = new Material(shader) { name = name };
                AssetDatabase.CreateAsset(m, path);
            }
            m.shader = shader;
            var col = AssetDatabase.LoadAssetAtPath<Texture2D>($"{Textures}/{tex}.png");
            var ms = AssetDatabase.LoadAssetAtPath<Texture2D>($"{Textures}/{tex}_MS.png");
            var glow = AssetDatabase.LoadAssetAtPath<Texture2D>($"{Textures}/{tex}_Glow.png");
            m.mainTexture = col;
            if (m.HasProperty("_BaseMap")) m.SetTexture("_BaseMap", col);
            if (m.HasProperty("_BaseColor")) m.SetColor("_BaseColor", Color.white);
            if (m.HasProperty("_MetallicGlossMap"))
            {
                m.SetTexture("_MetallicGlossMap", ms);
                m.EnableKeyword("_METALLICSPECGLOSSMAP");
                m.SetFloat("_SmoothnessTextureChannel", 0f);           // smoothness from the metallic map's alpha
                m.SetFloat("_Smoothness", 1f);
            }
            if (m.HasProperty("_EnvironmentReflections")) { m.SetFloat("_EnvironmentReflections", 1f); m.DisableKeyword("_ENVIRONMENTREFLECTIONS_OFF"); }
            if (emissive && m.HasProperty("_EmissionMap"))
            {
                m.SetTexture("_EmissionMap", glow);
                m.SetColor("_EmissionColor", new Color(0.5f, 0.45f, 1f) * 2f);
                m.globalIlluminationFlags = MaterialGlobalIlluminationFlags.RealtimeEmissive;   // URP keeps _EMISSION only with an emissive GI flag
                m.EnableKeyword("_EMISSION");
            }
            else
            {
                m.DisableKeyword("_EMISSION");
                if (m.HasProperty("_EmissionColor")) m.SetColor("_EmissionColor", Color.black);
            }
            EditorUtility.SetDirty(m);
            return m;
        }

        static Material Spark()
        {
            var texPath = $"{Textures}/T_Weapons_Spark.png";
            if (!File.Exists(texPath))
            {
                File.WriteAllBytes(texPath, WeaponGlow.DotTexture().EncodeToPNG());
                AssetDatabase.ImportAsset(texPath);
                var ti = (TextureImporter)AssetImporter.GetAtPath(texPath);
                ti.alphaIsTransparency = true;
                ti.sRGBTexture = true;
                ti.wrapMode = TextureWrapMode.Clamp;
                ti.SaveAndReimport();
            }
            var path = $"{Materials}/M_Weapons_Spark.mat";
            var m = AssetDatabase.LoadAssetAtPath<Material>(path);
            var sh = Shader.Find("Universal Render Pipeline/Particles/Unlit") ?? Shader.Find("Sprites/Default");
            if (m == null)
            {
                m = new Material(sh) { name = "M_Weapons_Spark" };
                AssetDatabase.CreateAsset(m, path);
            }
            m.shader = sh;
            WeaponGlow.MakeAdditive(m, AssetDatabase.LoadAssetAtPath<Texture2D>(texPath));
            EditorUtility.SetDirty(m);
            return m;
        }

        // ------------------------------------------------------------------------------------------------- prefabs
        static GameObject Prefab(Entry e, Material mat, Material spark)
        {
            var mesh = AssetDatabase.LoadAllAssetsAtPath($"{Models}/{e.name}.fbx").OfType<Mesh>().FirstOrDefault();
            if (mesh == null) return null;
            var go = new GameObject(e.name);
            try
            {
                go.AddComponent<MeshFilter>().sharedMesh = mesh;
                var mr = go.AddComponent<MeshRenderer>();
                mr.sharedMaterial = mat;
                var p = go.AddComponent<WeaponProp>();
                p.hand = e.hand;
                p.stringTop = V(e.string_top);
                p.stringBottom = V(e.string_bottom);
                p.boltRest = V(e.bolt_rest);
                p.length = e.length;
                p.triangles = e.tris;
                p.runed = e.runed;
                if (e.runed)
                {
                    var g = go.AddComponent<WeaponGlow>();
                    g.sparkMaterial = spark;
                }
                return PrefabUtility.SaveAsPrefabAsset(go, $"{Prefabs}/{e.name}.prefab");
            }
            finally { UnityEngine.Object.DestroyImmediate(go); }
        }

        // ------------------------------------------------------------------------------------------------- showcase
        static readonly Enchant[] Cycle = { Enchant.Flame, Enchant.Frost, Enchant.Storm, Enchant.Venom, Enchant.Holy, Enchant.Arcane };

        static string Category(Entry e)
        {
            if (IsShield(e)) return "shields";
            if (e.hand == "M" || e.hand == "L") return "ranged";
            if (e.length > 1.3f) return "long";
            if (e.length > 1.0f) return "twohand";
            return "onehand";
        }

        /// <summary>how a prop stands in the showcase: weapons as modelled (+Y up, flats to the camera), shields turned face
        /// to the camera (their +Y to -Z) and top up (their -X, Unity's side of Blender's +X up the shield)</summary>
        static Quaternion Turn(Entry e) => IsShield(e) ? Quaternion.LookRotation(Vector3.right, Vector3.back) : Quaternion.identity;

        /// <summary>the prop's bounds once turned</summary>
        static (Vector3 lo, Vector3 hi) Box(Entry e)
        {
            Vector3 a = V(e.bounds_min), b = V(e.bounds_max), q = Turn(e) * a;
            Vector3 lo = q, hi = q;
            for (int k = 1; k < 8; k++)
            {
                var c = Turn(e) * new Vector3((k & 1) != 0 ? b.x : a.x, (k & 2) != 0 ? b.y : a.y, (k & 4) != 0 ? b.z : a.z);
                lo = Vector3.Min(lo, c);
                hi = Vector3.Max(hi, c);
            }
            return (lo, hi);
        }

        static string BuildShowcase(List<Entry> list)
        {
            var path = $"{Scenes}/Weapons_Showcase.unity";
            var open = EditorSceneManager.GetActiveScene();
            string reopen = open.path;
            bool replace = !open.isDirty;
            var scene = replace ? EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single)
                                : EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Additive);
            var rootGo = new GameObject("Weapons_Showcase");
            SceneManager_Move(rootGo, scene);
            var sun = new GameObject("Sun").AddComponent<Light>();
            sun.type = LightType.Directional;
            sun.intensity = 1.6f;
            sun.color = new Color(1f, 0.96f, 0.9f);
            sun.transform.rotation = Quaternion.Euler(40f, 150f, 0f);
            sun.transform.SetParent(rootGo.transform);
            var fill = new GameObject("Fill").AddComponent<Light>();
            fill.type = LightType.Directional;
            fill.intensity = 0.5f;
            fill.color = new Color(0.75f, 0.82f, 1f);
            fill.transform.rotation = Quaternion.Euler(20f, -40f, 0f);
            fill.transform.SetParent(rootGo.transform);
            RenderSettings.ambientMode = AmbientMode.Trilight;
            RenderSettings.ambientSkyColor = new Color(0.55f, 0.6f, 0.68f);
            RenderSettings.ambientEquatorColor = new Color(0.42f, 0.42f, 0.42f);
            RenderSettings.ambientGroundColor = new Color(0.25f, 0.22f, 0.2f);

            var rows = new[] { "onehand", "twohand", "long", "ranged", "shields" };
            float rowY = 0f, prevBottom = 0f;
            bool first = true;
            int k = 0;
            var cams = new List<(Camera, string)>();
            foreach (var row in rows)
            {
                var items = list.Where(e => Category(e) == row).ToList();
                if (items.Count == 0) continue;
                float rowTop = items.Max(e => Box(e).hi.y);
                if (!first) rowY = prevBottom - 0.6f - rowTop;         // under the row above, whatever reaches up
                first = false;
                var parent = new GameObject("Row_" + row).transform;
                parent.SetParent(rootGo.transform);
                float x = 0f, top = 0f, bottom = 0f;
                foreach (var e in items)
                {
                    var pf = AssetDatabase.LoadAssetAtPath<GameObject>($"{Prefabs}/{e.name}.prefab");
                    if (pf == null) continue;
                    var go = (GameObject)PrefabUtility.InstantiatePrefab(pf, parent);
                    var (lo, hi) = Box(e);
                    float w = hi.x - lo.x;
                    go.transform.localPosition = new Vector3(x - lo.x, rowY, 0f);   // flats face the camera on -Z
                    go.transform.localRotation = Turn(e);
                    top = Mathf.Max(top, hi.y);
                    bottom = Mathf.Min(bottom, lo.y);
                    var g = go.GetComponent<WeaponGlow>();
                    if (g != null)
                    {
                        g.glowLight = false;                     // side by side, their lights would tint each other
                        g.Set(Cycle[k++ % Cycle.Length]);
                        foreach (var ps in go.GetComponentsInChildren<ParticleSystem>()) ps.Simulate(1.5f, true, true);
                    }
                    var label = new GameObject("Label_" + e.name).AddComponent<TextMesh>();
                    label.transform.SetParent(parent);
                    label.text = e.name.Replace("Wpn_", "").Replace("Shd_", "").Replace("_Rune", "\n(rune)");
                    label.characterSize = 0.005f;
                    label.fontSize = 64;
                    label.anchor = TextAnchor.UpperCenter;
                    label.alignment = TextAlignment.Center;
                    label.color = new Color(0.9f, 0.9f, 0.9f);
                    label.transform.localPosition = new Vector3(x + w * 0.5f, rowY + lo.y - 0.05f, 0f);
                    x += Mathf.Max(w, 0.12f) + 0.1f;
                }
                var cam = new GameObject("Cam_" + row).AddComponent<Camera>();
                cam.transform.SetParent(rootGo.transform);
                cam.orthographic = true;
                float h = top - bottom + 0.3f;
                cam.orthographicSize = Mathf.Max(h * 0.5f, x / (16f / 9f) * 0.5f) * 1.04f;
                cam.transform.position = new Vector3(x * 0.5f - 0.05f, rowY + (top + bottom) * 0.5f - 0.08f, -5f);
                cam.transform.rotation = Quaternion.identity;
                cam.clearFlags = CameraClearFlags.SolidColor;
                cam.backgroundColor = new Color(0.36f, 0.38f, 0.42f);
                cam.enabled = false;
                cams.Add((cam, row));
                prevBottom = rowY + bottom - 0.2f;                     // the labels hang under it
            }
            Directory.CreateDirectory(OutDir);
            bool async = ShaderUtil.allowAsyncCompilation;
            ShaderUtil.allowAsyncCompilation = false;            // else new variants render as nothing
            try { foreach (var (cam, row) in cams) Render(cam, $"showcase_{row}.png", 2400, 1350); }
            finally { ShaderUtil.allowAsyncCompilation = async; }
            EditorSceneManager.SaveScene(scene, path);
            if (!replace) EditorSceneManager.CloseScene(scene, true);
            else if (!string.IsNullOrEmpty(reopen) && reopen != path) EditorSceneManager.OpenScene(reopen);
            return $"  showcase {path}; renders in {OutDir}";
        }

        static void SceneManager_Move(GameObject go, UnityEngine.SceneManagement.Scene s) =>
            UnityEngine.SceneManagement.SceneManager.MoveGameObjectToScene(go, s);

        public static void Render(Camera cam, string file, int w, int h)
        {
            var rt = new RenderTexture(w, h, 24, RenderTextureFormat.ARGB32, RenderTextureReadWrite.sRGB) { antiAliasing = 4 };
            var req = new RenderPipeline.StandardRequest { destination = rt };
            if (GraphicsSettings.currentRenderPipeline != null && RenderPipeline.SupportsRenderRequest(cam, req))
                RenderPipeline.SubmitRenderRequest(cam, req);
            else
            {
                cam.targetTexture = rt;
                cam.Render();
                cam.targetTexture = null;
            }
            var prev = RenderTexture.active;
            RenderTexture.active = rt;
            var tex = new Texture2D(w, h, TextureFormat.RGB24, false);
            tex.ReadPixels(new Rect(0, 0, w, h), 0, 0);
            tex.Apply();
            RenderTexture.active = prev;
            Directory.CreateDirectory(OutDir);
            File.WriteAllBytes(Path.Combine(OutDir, file), tex.EncodeToPNG());
            UnityEngine.Object.DestroyImmediate(tex);
            rt.Release();
        }
    }
}
