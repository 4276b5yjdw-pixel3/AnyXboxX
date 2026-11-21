// anyxboxx_gpu_run.exe <shader.dxil> <mémoire.bin> [groupes]
//
// Exécute un shader de calcul DXIL produit par le recompilateur RDNA 2 → HLSL (emu/rdna2_hlsl.py)
// sur le GPU du PC, avec un seul buffer brut en u0 : la mémoire du programme. Le fichier
// mémoire est envoyé au GPU, le shader tourne, puis le fichier est réécrit avec le résultat.
// Sans GPU D3D12 (ou avec ANYXBOXX_GPU=warp), le rendu logiciel WARP de Windows est utilisé.
#include <windows.h>
#include <d3d12.h>
#include <dxgi1_6.h>
#include <wrl/client.h>

#include <cstdio>
#include <cstring>
#include <vector>

using Microsoft::WRL::ComPtr;

namespace {

constexpr UINT64 kAlignment = 4;  // RWByteAddressBuffer : taille multiple de 4 octets

int Fail(const char* what, HRESULT result = E_FAIL) {
  std::fprintf(stderr, "[gpu] %s (0x%08lx)\n", what, static_cast<unsigned long>(result));
  return 1;
}

bool ReadAll(const wchar_t* path, std::vector<char>& out) {
  FILE* file = nullptr;
  if (_wfopen_s(&file, path, L"rb") != 0 || file == nullptr) return false;
  char chunk[65536];
  for (size_t read; (read = std::fread(chunk, 1, sizeof chunk, file)) > 0;) out.insert(out.end(), chunk, chunk + read);
  std::fclose(file);
  return true;
}

bool WriteAll(const wchar_t* path, const char* data, size_t size) {
  FILE* file = nullptr;
  if (_wfopen_s(&file, path, L"wb") != 0 || file == nullptr) return false;
  const bool ok = std::fwrite(data, 1, size, file) == size;
  std::fclose(file);
  return ok;
}

bool WarpRequested() {
  wchar_t value[8] = {};
  return GetEnvironmentVariableW(L"ANYXBOXX_GPU", value, 8) > 0 && std::wcscmp(value, L"warp") == 0;
}

ComPtr<ID3D12Device> CreateDevice(const char** kind) {
  ComPtr<ID3D12Device> device;
  if (!WarpRequested() && SUCCEEDED(D3D12CreateDevice(nullptr, D3D_FEATURE_LEVEL_11_0, IID_PPV_ARGS(&device)))) {
    *kind = "matériel";
    return device;
  }
  ComPtr<IDXGIFactory4> factory;
  ComPtr<IDXGIAdapter> warp;
  if (SUCCEEDED(CreateDXGIFactory2(0, IID_PPV_ARGS(&factory))) && SUCCEEDED(factory->EnumWarpAdapter(IID_PPV_ARGS(&warp)))) {
    D3D12CreateDevice(warp.Get(), D3D_FEATURE_LEVEL_11_0, IID_PPV_ARGS(&device));
  }
  *kind = "WARP";
  return device;
}

ComPtr<ID3D12Resource> Buffer(ID3D12Device* device, D3D12_HEAP_TYPE type, UINT64 size, D3D12_RESOURCE_FLAGS flags,
                              D3D12_RESOURCE_STATES state) {
  D3D12_HEAP_PROPERTIES heap = {};
  heap.Type = type;
  D3D12_RESOURCE_DESC desc = {};
  desc.Dimension = D3D12_RESOURCE_DIMENSION_BUFFER;
  desc.Width = size;
  desc.Height = 1;
  desc.DepthOrArraySize = 1;
  desc.MipLevels = 1;
  desc.SampleDesc.Count = 1;
  desc.Layout = D3D12_TEXTURE_LAYOUT_ROW_MAJOR;
  desc.Flags = flags;
  ComPtr<ID3D12Resource> resource;
  device->CreateCommittedResource(&heap, D3D12_HEAP_FLAG_NONE, &desc, state, nullptr, IID_PPV_ARGS(&resource));
  return resource;
}

void Transition(ID3D12GraphicsCommandList* list, ID3D12Resource* resource, D3D12_RESOURCE_STATES before,
                D3D12_RESOURCE_STATES after) {
  D3D12_RESOURCE_BARRIER barrier = {};
  barrier.Type = D3D12_RESOURCE_BARRIER_TYPE_TRANSITION;
  barrier.Transition.pResource = resource;
  barrier.Transition.Subresource = D3D12_RESOURCE_BARRIER_ALL_SUBRESOURCES;
  barrier.Transition.StateBefore = before;
  barrier.Transition.StateAfter = after;
  list->ResourceBarrier(1, &barrier);
}

ComPtr<ID3D12PipelineState> Pipeline(ID3D12Device* device, const std::vector<char>& shader,
                                     ComPtr<ID3D12RootSignature>& root) {
  D3D12_ROOT_PARAMETER parameter = {};
  parameter.ParameterType = D3D12_ROOT_PARAMETER_TYPE_UAV;  // u0 : la mémoire, buffer brut
  parameter.ShaderVisibility = D3D12_SHADER_VISIBILITY_ALL;
  D3D12_ROOT_SIGNATURE_DESC desc = {1, &parameter, 0, nullptr, D3D12_ROOT_SIGNATURE_FLAG_NONE};
  ComPtr<ID3DBlob> blob;
  ComPtr<ID3DBlob> error;
  if (FAILED(D3D12SerializeRootSignature(&desc, D3D_ROOT_SIGNATURE_VERSION_1, &blob, &error)) ||
      FAILED(device->CreateRootSignature(0, blob->GetBufferPointer(), blob->GetBufferSize(), IID_PPV_ARGS(&root)))) {
    return nullptr;
  }
  D3D12_COMPUTE_PIPELINE_STATE_DESC pipeline = {};
  pipeline.pRootSignature = root.Get();
  pipeline.CS = {shader.data(), shader.size()};
  ComPtr<ID3D12PipelineState> state;
  device->CreateComputePipelineState(&pipeline, IID_PPV_ARGS(&state));
  return state;
}

}  // namespace

int wmain(int argc, wchar_t** argv) {
  if (argc < 3) {
    std::fwprintf(stderr, L"Usage : anyxboxx_gpu_run.exe <shader.dxil> <mémoire.bin> [groupes]\n");
    return 2;
  }
  std::vector<char> shader;
  std::vector<char> memory;
  if (!ReadAll(argv[1], shader) || !ReadAll(argv[2], memory)) return Fail("lecture des fichiers impossible");
  const size_t original = memory.size();
  memory.resize((memory.size() + kAlignment - 1) / kAlignment * kAlignment + kAlignment);
  const UINT groups = argc > 3 ? static_cast<UINT>(_wtoi(argv[3])) : 1;

  const char* kind = "";
  ComPtr<ID3D12Device> device = CreateDevice(&kind);
  if (!device) return Fail("aucun périphérique D3D12");
  ComPtr<ID3D12RootSignature> root;
  ComPtr<ID3D12PipelineState> pipeline = Pipeline(device.Get(), shader, root);
  if (!pipeline) return Fail("shader DXIL refusé (signature ou format)");

  const UINT64 size = memory.size();
  ComPtr<ID3D12Resource> gpu = Buffer(device.Get(), D3D12_HEAP_TYPE_DEFAULT, size,
                                      D3D12_RESOURCE_FLAG_ALLOW_UNORDERED_ACCESS, D3D12_RESOURCE_STATE_COPY_DEST);
  ComPtr<ID3D12Resource> upload = Buffer(device.Get(), D3D12_HEAP_TYPE_UPLOAD, size, D3D12_RESOURCE_FLAG_NONE,
                                         D3D12_RESOURCE_STATE_GENERIC_READ);
  ComPtr<ID3D12Resource> readback = Buffer(device.Get(), D3D12_HEAP_TYPE_READBACK, size, D3D12_RESOURCE_FLAG_NONE,
                                           D3D12_RESOURCE_STATE_COPY_DEST);
  if (!gpu || !upload || !readback) return Fail("allocation des buffers impossible");
  void* mapped = nullptr;
  if (FAILED(upload->Map(0, nullptr, &mapped))) return Fail("Map du buffer d'envoi");
  std::memcpy(mapped, memory.data(), memory.size());
  upload->Unmap(0, nullptr);

  D3D12_COMMAND_QUEUE_DESC queue_desc = {};
  queue_desc.Type = D3D12_COMMAND_LIST_TYPE_DIRECT;
  ComPtr<ID3D12CommandQueue> queue;
  ComPtr<ID3D12CommandAllocator> allocator;
  ComPtr<ID3D12GraphicsCommandList> list;
  ComPtr<ID3D12Fence> fence;
  if (FAILED(device->CreateCommandQueue(&queue_desc, IID_PPV_ARGS(&queue))) ||
      FAILED(device->CreateCommandAllocator(D3D12_COMMAND_LIST_TYPE_DIRECT, IID_PPV_ARGS(&allocator))) ||
      FAILED(device->CreateCommandList(0, D3D12_COMMAND_LIST_TYPE_DIRECT, allocator.Get(), pipeline.Get(),
                                       IID_PPV_ARGS(&list))) ||
      FAILED(device->CreateFence(0, D3D12_FENCE_FLAG_NONE, IID_PPV_ARGS(&fence)))) {
    return Fail("création de la file de commandes");
  }
  list->CopyBufferRegion(gpu.Get(), 0, upload.Get(), 0, size);
  Transition(list.Get(), gpu.Get(), D3D12_RESOURCE_STATE_COPY_DEST, D3D12_RESOURCE_STATE_UNORDERED_ACCESS);
  list->SetComputeRootSignature(root.Get());
  list->SetComputeRootUnorderedAccessView(0, gpu->GetGPUVirtualAddress());
  list->Dispatch(groups, 1, 1);
  Transition(list.Get(), gpu.Get(), D3D12_RESOURCE_STATE_UNORDERED_ACCESS, D3D12_RESOURCE_STATE_COPY_SOURCE);
  list->CopyBufferRegion(readback.Get(), 0, gpu.Get(), 0, size);
  if (FAILED(list->Close())) return Fail("fermeture de la liste de commandes");
  ID3D12CommandList* lists[] = {list.Get()};
  queue->ExecuteCommandLists(1, lists);
  HANDLE done = CreateEventW(nullptr, FALSE, FALSE, nullptr);
  queue->Signal(fence.Get(), 1);
  fence->SetEventOnCompletion(1, done);
  WaitForSingleObject(done, INFINITE);
  CloseHandle(done);
  if (FAILED(device->GetDeviceRemovedReason())) return Fail("périphérique perdu pendant le calcul", device->GetDeviceRemovedReason());

  if (FAILED(readback->Map(0, nullptr, &mapped))) return Fail("Map du buffer de lecture");
  const bool written = WriteAll(argv[2], static_cast<const char*>(mapped), original);
  readback->Unmap(0, nullptr);
  if (!written) return Fail("écriture du résultat impossible");
  std::printf("[gpu] %s : %u groupe(s) exécuté(s)\n", kind, groups);
  return 0;
}
