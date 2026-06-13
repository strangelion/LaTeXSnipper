#pragma once

// Lightweight CComPtr replacement to eliminate the ATL SDK dependency.
// Provides the same AddRef/Release semantics for COM interface pointers.

#include <unknwn.h>

namespace ATL {

template <class T>
class CComPtr {
public:
    CComPtr() noexcept : p_(nullptr) {}
    CComPtr(T* lp) noexcept : p_(lp) { if (p_) p_->AddRef(); }
    CComPtr(const CComPtr<T>& lp) noexcept : p_(lp.p_) { if (p_) p_->AddRef(); }
    CComPtr(CComPtr<T>&& lp) noexcept : p_(lp.p_) { lp.p_ = nullptr; }

    ~CComPtr() noexcept { if (p_) p_->Release(); }

    CComPtr<T>& operator=(T* lp) noexcept {
        if (p_ != lp) {
            if (p_) p_->Release();
            p_ = lp;
            if (p_) p_->AddRef();
        }
        return *this;
    }

    CComPtr<T>& operator=(const CComPtr<T>& lp) noexcept { return *this = lp.p_; }
    CComPtr<T>& operator=(CComPtr<T>&& lp) noexcept {
        if (this != &lp) {
            if (p_) p_->Release();
            p_ = lp.p_;
            lp.p_ = nullptr;
        }
        return *this;
    }

    void Release() noexcept {
        T* p = p_;
        p_ = nullptr;
        if (p) p->Release();
    }

    operator T*() const noexcept { return p_; }
    T& operator*() const noexcept { return *p_; }
    T** operator&() noexcept { Release(); return &p_; }
    T* operator->() const noexcept { return p_; }
    T* Get() const noexcept { return p_; }

    bool operator!() const noexcept { return p_ == nullptr; }
    bool operator==(T* p) const noexcept { return p_ == p; }

private:
    T* p_;
};

} // namespace ATL
