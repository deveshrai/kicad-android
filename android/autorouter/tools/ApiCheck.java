// Lists the JDK classes and methods that compiled classes use but android.jar does not have.
// Usage: java ApiCheck.java android.jar classes-dir [more class dirs]

import java.lang.classfile.*;
import java.lang.classfile.constantpool.*;
import java.nio.file.*;
import java.util.*;
import java.util.zip.*;

public class ApiCheck {
  static Map<String, ClassModel> lib = new HashMap<>();
  static Set<String> app = new HashSet<>();
  static boolean has(String owner, String name, String desc) {
    Deque<String> q = new ArrayDeque<>(List.of(owner)); Set<String> seen = new HashSet<>();
    while (!q.isEmpty()) {
      String c = q.poll(); if (!seen.add(c)) continue;
      if (app.contains(c)) return true;
      ClassModel m = lib.get(c); if (m == null) continue;
      for (MethodModel mm : m.methods()) if (mm.methodName().stringValue().equals(name) && (desc == null || mm.methodType().stringValue().equals(desc))) return true;
      for (FieldModel fm : m.fields()) if (desc == null && fm.fieldName().stringValue().equals(name)) return true;
      m.superclass().ifPresent(s -> q.add(s.asInternalName()));
      for (ClassEntry i : m.interfaces()) q.add(i.asInternalName());
    }
    return false;
  }
  public static void main(String[] a) throws Exception {
    try (ZipFile z = new ZipFile(a[0])) {
      for (var e : Collections.list(z.entries())) if (e.getName().endsWith(".class")) {
        ClassModel m = ClassFile.of().parse(z.getInputStream(e).readAllBytes()); lib.put(m.thisClass().asInternalName(), m); }
    }
    List<Path> cls = new ArrayList<>();
    for (int i = 1; i < a.length; i++) try (var s = Files.walk(Path.of(a[i]))) { s.filter(p -> p.toString().endsWith(".class")).forEach(cls::add); }
    List<ClassModel> models = new ArrayList<>();
    for (Path p : cls) { ClassModel m = ClassFile.of().parse(Files.readAllBytes(p)); models.add(m); app.add(m.thisClass().asInternalName()); }
    TreeMap<String, TreeSet<String>> miss = new TreeMap<>();
    for (ClassModel m : models) for (PoolEntry pe : m.constantPool()) {
      String owner, name, desc;
      if (pe instanceof MemberRefEntry r) { owner = r.owner().asInternalName(); name = r.name().stringValue(); desc = (pe instanceof FieldRefEntry) ? null : r.type().stringValue(); }
      else if (pe instanceof ClassEntry c) { owner = c.asInternalName(); name = null; desc = null; }
      else continue;
      if (owner.startsWith("[")) continue;
      if (!(owner.startsWith("java/") || owner.startsWith("javax/") || owner.startsWith("jdk/") || owner.startsWith("sun/") || owner.startsWith("com/sun/"))) { if (!app.contains(owner) && !lib.containsKey(owner)) miss.computeIfAbsent("CLASS(non-jdk) " + owner, k -> new TreeSet<>()).add(m.thisClass().asInternalName()); continue; }
      if (!lib.containsKey(owner)) { miss.computeIfAbsent("CLASS " + owner, k -> new TreeSet<>()).add(m.thisClass().asInternalName()); continue; }
      if (name != null && !has(owner, name, desc)) miss.computeIfAbsent("METHOD " + owner + "." + name + (desc == null ? "" : desc), k -> new TreeSet<>()).add(m.thisClass().asInternalName());
    }
    miss.forEach((k, v) -> System.out.println(k + "  <- " + v));
  }
}
